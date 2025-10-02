import os
import json
from pydantic import BaseModel
from typing import List
from datetime import date, timedelta

import asyncio
import aiohttp
from dateutil.relativedelta import relativedelta
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, Date
from sqlalchemy.orm import Session
import plotly.graph_objects as go

from . import models
from . import database
from . import system_prompt
from . import postprocessing


# --- КОНФИГУРАЦИЯ vLLM ---
VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8100/v1/chat/completions")
MODEL_NAME = "JosephThePatrician/qwen3_0.6b-reviews-fine-tune-v3"
turn_qwen_thinking_off = ("qwen3" in MODEL_NAME)
MAX_CONNECTIONS = 100 # Ограничиваем количество одновременных запросов к vLLM
MAX_RETRIES = 3       # Количество повторных попыток для каждого отзыва


models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()

origins = ["http://localhost:3000", "http://localhost:8080"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Словарь для перевода тональности
SENTIMENT_MAP = {
    "positive": "положительно",
    "negative": "отрицательно",
    "neutral": "нейтрально",
}

# Модели для валидации запроса и ответа
class ReviewRequestItem(BaseModel):
    id: int
    text: str

class PredictRequest(BaseModel):
    data: List[ReviewRequestItem]

def validate_response_structure(pairs: list) -> bool:
    """Проверяет, что ответ соответствует требуемой структуре"""
    try:
        if not isinstance(pairs, list):
            return False  
        for pair in pairs:
            if not isinstance(pair, dict):
                return False
            if len(pair) != 2:
                return False
            if "topic" not in pair or "sentiment" not in pair:
                return False
            if pair["sentiment"] not in ["positive", "negative", "neutral"]:
                return False
        return True
    except Exception:
        return False

async def process_single_review(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    review_item: ReviewRequestItem
):
    # print("review_item", review_item)
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                payload = {
                    "model": MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": system_prompt.SYSTEM_PROMPT},
                        {"role": "user", "content": review_item.text + " /no_think" * turn_qwen_thinking_off}
                    ],
                    "temperature": 0.5,
                    "max_tokens": 250,
                }
                # print("payload", payload)
                async with session.post(VLLM_URL, json=payload, timeout=180) as response: # Добавляем таймаут
                    if response.status == 200:
                        response_data = await response.json()
                        # print("response_data", response_data)
                        content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                        # print("content", content)
                        try:

                            parsed_response = json.loads(content.replace("'", "\"")) # Обучали на одинарных кавычках
                            # print("parsed_response", parsed_response)
                            if not validate_response_structure(parsed_response):
                                continue # Невалидная структура, retry

                            topics = [item["topic"] for item in parsed_response]
                            sentiments = [SENTIMENT_MAP[item["sentiment"]] for item in parsed_response]
                            return {"id": review_item.id, "topics": topics, "sentiments": sentiments}

                        except (json.JSONDecodeError, TypeError) as e:
                            # Модель вернула невалидный JSON, попробуем еще раз
                            print(f"Попытка {attempt + 1} провалена: Ошибка сети/таймаута - {e}")
                            pass
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                # Таймаут запроса, попробуем еще раз
                print(f"Попытка {attempt + 1} провалена: Ошибка сети/таймаута - {e}")
                pass
            except Exception as e:
                # Любая другая ошибка, попробуем еще раз
                print(f"Попытка {attempt + 1} провалена: Неизвестная ошибка - {e}")
                pass
            
            # Если дошли сюда, значит была ошибка, ждем перед повторной попыткой
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)

    # Если все попытки провалились, возвращаем пустой результат для этого отзыва
    return {"id": review_item.id, "topics": [], "sentiments": []}


@app.post("/api/predict")
async def predict_sentiments(request: PredictRequest):
    # Проверка на пустые данные согласно ТЗ
    # print("request", request)
    if not request.data:
        return JSONResponse(
            status_code=400,
            content={"error": "Пустые данные. 'data' не может быть пустым списком."}
        )  
    semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
    async with aiohttp.ClientSession() as session:
        tasks = [process_single_review(session, semaphore, item) for item in request.data]
        predictions = await asyncio.gather(*tasks)
        
    return {"predictions": predictions}


def format_date_label(date_obj, granularity):
    if granularity == 'month':
        months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
        return f"{months[date_obj.month - 1]} {date_obj.year}"
    if granularity == 'week':
        return f"W{date_obj.isocalendar().week} {date_obj.year}"
    return date_obj.strftime('%d.%m.%Y')


@app.get("/api/kpi_summary")
async def get_kpi_summary(
    products: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = 'month', # Гранулярность нужна для расчета тренда
    db: Session = Depends(get_db)
):
    print('---[ДЕБАГ: Backend Endpoint]---')
    print(f'Получен start_date: {start_date} (тип: {type(start_date)})')
    print(f'Получен end_date: {end_date} (тип: {type(end_date)})')

    topic_list = [p.strip() for p in products.split(',')] if products else None

    # Вспомогательная функция для получения данных за период
    def get_counts_for_period(period_start, period_end):
        """Получение данных за период"""
        if not period_start or not period_end:
            return {"positive": 0, "neutral": 0, "negative": 0}
            
        query = db.query(
            models.ReviewTopicLink.sentiment,
            func.count(models.ReviewTopicLink.id)
        ).join(models.Review)

        if topic_list:
            query = query.join(models.Topic).filter(models.Topic.name.in_(topic_list))
        
        # Явно приводим тип поля в БД к Date для корректного сравнения
        query = query.filter(func.cast(models.Review.date, Date).between(period_start, period_end))

        counts = query.group_by(models.ReviewTopicLink.sentiment).all()
        result = {"positive": 0, "neutral": 0, "negative": 0}
        for sentiment, count in counts:
            result[sentiment.lower()] = count
        return result

    # 1. Считаем ОСНОВНЫЕ ЗНАЧЕНИЯ за ВЕСЬ выбранный период
    total_period_counts = get_counts_for_period(start_date, end_date)
    
    # 2. Определяем периоды для РАСЧЕТА ТРЕНДА (последний и предпоследний)
    if end_date:
        if granularity == 'day':
            last_interval_start = end_date
            previous_interval_start = end_date - timedelta(days=1)
            previous_interval_end = end_date - timedelta(days=1)
        elif granularity == 'week':
            # Начало недели, в которую попадает end_date
            last_interval_start = end_date - timedelta(days=end_date.weekday())
            previous_interval_start = last_interval_start - timedelta(weeks=1)
            previous_interval_end = last_interval_start - timedelta(days=1)
        else: # month
            # Начало месяца, в который попадает end_date
            last_interval_start = end_date.replace(day=1)
            previous_interval_start = last_interval_start - relativedelta(months=1)
            previous_interval_end = last_interval_start - timedelta(days=1)

        # Данные за последний интервал (с начала последнего периода до end_date)
        last_interval_counts = get_counts_for_period(last_interval_start, end_date)
        
        # Данные за предпоследний интервал (полный предпоследний период)
        previous_interval_counts = get_counts_for_period(previous_interval_start, previous_interval_end)
    else:
        # Если end_date не задан, тренды посчитать невозможно
        last_interval_counts = {"positive": 0, "neutral": 0, "negative": 0}
        previous_interval_counts = {"positive": 0, "neutral": 0, "negative": 0}

    # 3. Формируем итоговый результат
    kpi_abs = {}
    for sentiment in ["positive", "neutral", "negative"]:
        kpi_abs[sentiment] = {
            "value": total_period_counts[sentiment],
            # ИЗМЕНЕНИЕ 7: Тренд для абсолютных значений теперь считается как абсолютная разница (в шт.)
            "trend": last_interval_counts[sentiment] - previous_interval_counts[sentiment]
        }
        
    total_current = sum(total_period_counts.values())
    
    total_last_interval = sum(last_interval_counts.values())
    total_previous_interval = sum(previous_interval_counts.values())

    kpi_perc = {}
    for sentiment in ["positive", "neutral", "negative"]:
        current_perc_total = (total_period_counts[sentiment] / total_current * 100) if total_current > 0 else 0
        perc_last_interval = (last_interval_counts[sentiment] / total_last_interval * 100) if total_last_interval > 0 else 0
        perc_previous_interval = (previous_interval_counts[sentiment] / total_previous_interval * 100) if total_previous_interval > 0 else 0
        
        kpi_perc[sentiment] = {
            "value": round(current_perc_total),
            # Тренд для процентов остается как разница в п.п.
            "trend": round(perc_last_interval - perc_previous_interval)
        }

    return {"kpiAbs": kpi_abs, "kpiPerc": kpi_perc}


@app.get("/api/key_aspects")
async def get_key_aspects(
    products: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db)
):
    """Эндпоинт для таблицы "Ключевые аспекты"""
    def get_top_aspects(sentiment_filter):
        query = db.query(
            models.Topic.name.label("aspect"),
            func.count(models.ReviewTopicLink.id).label("count")
        ).select_from(models.ReviewTopicLink).join(models.Topic).join(models.Review)
        
        if products:
            query = query.filter(models.Topic.name.in_([p.strip() for p in products.split(',')]))
        
        if start_date and end_date:
            # Явно приводим тип поля в БД к Date для корректного сравнения
            query = query.filter(func.cast(models.Review.date, Date).between(start_date, end_date))

        results = query.filter(models.ReviewTopicLink.sentiment.ilike(sentiment_filter)).group_by(models.Topic.name).order_by(func.count(models.ReviewTopicLink.id).desc()).limit(5).all()
        return [{"aspect": r.aspect, "sentiment": sentiment_filter.lower(), "count": r.count, "trend": 0} for r in results]

    positive_aspects = get_top_aspects("positive")
    negative_aspects = get_top_aspects("negative")
    return positive_aspects + negative_aspects


def create_dynamics_data(
    products: str | None,
    start_date: date | None,
    end_date: date | None,
    granularity: str,
    db: Session
):
    """Вспомогательная функция для графиков"""
    if granularity == 'day':
        sql_trunc_unit = 'day'
    elif granularity == 'week':
        sql_trunc_unit = 'week'
    else:
        sql_trunc_unit = 'month'
        
    base_query = db.query(models.ReviewTopicLink).join(models.Review)

    if products:
        topic_list = [p.strip() for p in products.split(',')]
        base_query = base_query.join(models.Topic).filter(models.Topic.name.in_(topic_list))
    
    if start_date and end_date:
        # Явно приводим тип поля в БД к Date для корректного сравнения
        base_query = base_query.filter(func.cast(models.Review.date, Date).between(start_date, end_date))
    
    group_date_col = func.date_trunc(sql_trunc_unit, models.Review.date).cast(Date).label("group_date")

    results = base_query.with_entities(
        group_date_col,
        models.ReviewTopicLink.sentiment,
        func.count(models.ReviewTopicLink.id).label("count")
    ).group_by("group_date", models.ReviewTopicLink.sentiment).order_by("group_date").all()
    
    data = {}
    for row in results:
        if row.group_date:
            data.setdefault(row.group_date, {})[row.sentiment.lower()] = row.count

    raw_categories_dates = sorted(data.keys())
    formatted_categories = [format_date_label(d, granularity) for d in raw_categories_dates]
    
    return data, raw_categories_dates, formatted_categories


@app.get("/api/dynamics")
async def get_dynamics_chart_data(
    products: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = 'month',
    db: Session = Depends(get_db)
):
    """Эндпоинт для графика долей (%)"""
    data, raw_categories_dates, formatted_categories = create_dynamics_data(products, start_date, end_date, granularity, db)

    series_data = {s: [] for s in ['positive', 'negative', 'neutral']}
    for date_key in raw_categories_dates:
        total = sum(data.get(date_key, {}).values())
        for sentiment in series_data:
            count = data.get(date_key, {}).get(sentiment, 0)
            series_data[sentiment].append((count / total) * 100 if total > 0 else 0)
            
    fig = go.Figure()
    colors = {'positive': '#00875A', 'negative': '#DE350B', 'neutral': '#FFA500'}
    names = {'positive': 'Позитивные', 'negative': 'Негативные', 'neutral': 'Нейтральные'}
    sentiments_order = ['positive', 'neutral', 'negative']

    for sentiment in sentiments_order:
        fig.add_trace(go.Scatter(
            x=formatted_categories, y=series_data[sentiment], name=names[sentiment],
            mode='lines', stackgroup='one', line=dict(width=0.5, color=colors[sentiment]),
            fillcolor=colors[sentiment] # Добавляем цвет заливки
        ))
        
    fig.update_layout(
        template="plotly_white", yaxis_title="Доля, %",
        margin=dict(t=10, b=10, l=40, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return json.loads(fig.to_json())


@app.get("/api/dynamics_stacked_bar")
async def get_dynamics_stacked_bar(
    products: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = 'month',
    db: Session = Depends(get_db)
):
    """Эндпоинт для графика количества (stacked bar)"""
    data, raw_categories_dates, formatted_categories = create_dynamics_data(products, start_date, end_date, granularity, db)
        
    fig = go.Figure()
    sentiments_order = ['positive', 'neutral', 'negative']
    colors = {'positive': '#00875A', 'negative': '#DE350B', 'neutral': '#FFA500'}
    names = {'positive': 'Позитивные', 'negative': 'Негативные', 'neutral': 'Нейтральные'}

    for sentiment in sentiments_order:
        counts = [data.get(date_key, {}).get(sentiment, 0) for date_key in raw_categories_dates]
        fig.add_trace(go.Bar(
            name=names[sentiment], x=formatted_categories, y=counts,
            marker_color=colors[sentiment]
        ))

    fig.update_layout(
        barmode='stack', template="plotly_white", yaxis_title="Количество отзывов",
        margin=dict(t=10, b=10, l=40, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return json.loads(fig.to_json())


@app.get("/api/reviews")
async def get_reviews(
    products: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db)
):
    """Эндпоинт для списка отзывов"""
    base_query = db.query(models.Review)
    if products:
        topic_list = [p.strip() for p in products.split(',')]
        review_ids_query = db.query(models.ReviewTopicLink.review_id).join(models.Topic).filter(models.Topic.name.in_(topic_list))
        review_ids = [r.review_id for r in review_ids_query.distinct().all()]
        base_query = base_query.filter(models.Review.id.in_(review_ids))

    if start_date and end_date:
        # Явно приводим тип поля в БД к Date для корректного сравнения
        base_query = base_query.filter(func.cast(models.Review.date, Date).between(start_date, end_date))

    latest_reviews = base_query.order_by(models.Review.date.desc()).limit(50).all()
    return [{"id": r.id, "product": r.source_topic, "text": r.review_text, "sentiment": r.topics[0].sentiment if r.topics else "N/A", "cluster": ", ".join([link.topic.name for link in r.topics]), "date": r.date.isoformat() if r.date else None} for r in latest_reviews]


@app.get("/api/products_list")
async def get_products_list(db: Session = Depends(get_db)):
    """Эндпоинт для списка продуктов"""
    topics_query = db.query(models.Topic.name).distinct().order_by(models.Topic.name)
    return [t.name for t in topics_query.all()]