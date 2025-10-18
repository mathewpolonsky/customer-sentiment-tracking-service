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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    print(review_item.text)
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
                async with session.post(VLLM_URL, json=payload, timeout=180) as response: # Добавляем таймаут
                    if response.status == 200:
                        response_data = await response.json()
                        content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                        try:
                            content = content.replace("<think>\n\n</think>", "").strip()
                            parsed_response = json.loads(content.replace("'", "\"")) # Обучали на одинарных кавычках
                            if not validate_response_structure(parsed_response):
                                continue # Невалидная структура, retry

                            parsed_response = postprocessing.process_pairs(parsed_response, return_subtopics=False)

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


def expand_topics_with_subtopics(topic_list: List[str]) -> List[str]:
    """
    Принимает список основных тем и расширяет его, 
    добавляя все вложенные подтемы.
    """
    full_list = set(topic_list)
    for topic in topic_list:
        # Исправляем обращение к словарю
        if topic in postprocessing.topics_subtopics:
            for subtopic in postprocessing.topics_subtopics[topic]:
                full_list.add(subtopic)
    return list(full_list)


def aggregate_sentiments(
    db_results: list,
    selected_main_topics: list
) -> dict:
    """
    Агрегирует "сырые" результаты из БД, правильно распределяя подтемы
    по нескольким родительским темам.
    """
    # Инициализируем счетчики нулями
    aggregated_counts = {
        "positive": 0,
        "neutral": 0,
        "negative": 0
    }

    # Создаем словарь для подсчета уникальных отзывов, чтобы не считать один и тот же отзыв дважды
    # если он попал под две выбранные категории (например, "Дебетовые карты" и "Премиум")
    processed_review_links = set()

    for review_link_id, topic_name, sentiment in db_results:
        if review_link_id in processed_review_links:
            continue

        # Находим все родительские темы для текущей темы/подтемы из отзыва
        parent_topics = postprocessing.subtopic_to_topics_map.get(topic_name, [])

        # Проверяем, пересекаются ли родительские темы отзыва с темами, выбранными пользователем
        if any(pt in selected_main_topics for pt in parent_topics):
            aggregated_counts[sentiment.lower()] += 1
            processed_review_links.add(review_link_id)

    return aggregated_counts


def format_date_label(date_obj, granularity):
    if granularity == 'month':
        months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
        return f"{months[date_obj.month - 1]} {date_obj.year}"
    if granularity == 'week':
        # Заменяем "W" на русскую "Н"
        return f"Н{date_obj.isocalendar().week} {date_obj.year}"
    return date_obj.strftime('%d.%m.%Y')


@app.get("/api/kpi_summary")
async def get_kpi_summary(
    products: str | None = None,
    sources: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = 'month',
    db: Session = Depends(get_db)
):
    selected_main_topics = [p.strip() for p in products.split(',')] if products else []
    
    # Helper-функция для получения сырых данных
    def get_raw_data_for_period(period_start, period_end, main_topics): # <-- 1. ПРИНИМАЕМ темы как аргумент
        if not main_topics or not period_start or not period_end:
            return []

        # Расширяем темы для эффективного WHERE IN (...) запроса к БД
        topics_to_fetch = expand_topics_with_subtopics(main_topics)

        query = db.query(
            models.ReviewTopicLink.id,
            models.Topic.name,
            models.ReviewTopicLink.sentiment
        ).join(models.Review).join(models.Topic)

        query = query.filter(models.Topic.name.in_(topics_to_fetch))

        if sources:
            source_list = [s.strip() for s in sources.split(',')]
            query = query.filter(models.Review.source.in_(source_list))
        
        query = query.filter(func.cast(models.Review.date, Date).between(period_start, period_end))

        return query.all()

    # Определяем периоды для РАСЧЕТА ТРЕНДА
    if end_date:
        if granularity == 'day':
            last_interval_start = end_date
            previous_interval_start = end_date - timedelta(days=1)
            previous_interval_end = end_date - timedelta(days=1)
        elif granularity == 'week':
            last_interval_start = end_date - timedelta(days=end_date.weekday())
            previous_interval_start = last_interval_start - timedelta(weeks=1)
            previous_interval_end = last_interval_start - timedelta(days=1)
        else: # month
            last_interval_start = end_date.replace(day=1)
            previous_interval_start = last_interval_start - relativedelta(months=1)
            previous_interval_end = last_interval_start - timedelta(days=1)
    else:
        last_interval_start = None
        previous_interval_start = None
        previous_interval_end = None

    # 1. Получаем сырые данные за периоды
    raw_total_data = get_raw_data_for_period(start_date, end_date, selected_main_topics)
    raw_last_interval_data = get_raw_data_for_period(last_interval_start, end_date, selected_main_topics) if end_date else []
    raw_previous_interval_data = get_raw_data_for_period(previous_interval_start, previous_interval_end, selected_main_topics) if end_date else []

    # 2. Агрегируем данные с помощью новой логики
    total_period_counts = aggregate_sentiments(raw_total_data, selected_main_topics)
    last_interval_counts = aggregate_sentiments(raw_last_interval_data, selected_main_topics)
    previous_interval_counts = aggregate_sentiments(raw_previous_interval_data, selected_main_topics)

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
    sentiments = ["positive", "neutral", "negative"]

    if total_current > 0:
        # 1. Вычисляем "сырые" проценты
        raw_percentages = {s: (total_period_counts[s] / total_current * 100) for s in sentiments}
        
        # 2. Округляем всё вниз (получаем целые части)
        rounded_percentages = {s: int(p) for s, p in raw_percentages.items()}
        
        # 3. Считаем, сколько единиц "потерялось" при округлении
        deficit = 100 - sum(rounded_percentages.values())
        
        # 4. Сортируем тональности по убыванию их дробной части (raw - int)
        sentiments_to_increment = sorted(
            sentiments, 
            key=lambda s: raw_percentages[s] - rounded_percentages[s], 
            reverse=True
        )
        
        # 5. Распределяем "потерянные" единицы по одной, начиная с тех, 
        #    у кого была самая большая дробная часть
        for i in range(deficit):
            rounded_percentages[sentiments_to_increment[i]] += 1
            
        # Теперь rounded_percentages содержит корректные значения
        for sentiment in sentiments:
            kpi_perc.setdefault(sentiment, {})['value'] = rounded_percentages[sentiment]
            
    else:
        # Если нет данных, просто ставим нули
        for sentiment in sentiments:
             kpi_perc.setdefault(sentiment, {})['value'] = 0

    # Расчет тренда остается без изменений
    for sentiment in sentiments:
        perc_last_interval = (last_interval_counts[sentiment] / total_last_interval * 100) if total_last_interval > 0 else 0
        perc_previous_interval = (previous_interval_counts[sentiment] / total_previous_interval * 100) if total_previous_interval > 0 else 0
        kpi_perc.setdefault(sentiment, {})['trend'] = round(perc_last_interval - perc_previous_interval) 

    return {"kpiAbs": kpi_abs, "kpiPerc": kpi_perc}


def create_dynamics_data(
    products: str | None,
    sources: str | None,
    start_date: date | None,
    end_date: date | None,
    granularity: str,
    db: Session
):
    selected_main_topics = [p.strip() for p in products.split(',')] if products else []
    if not selected_main_topics:
        return {}, [], []

    if granularity == 'day': sql_trunc_unit = 'day'
    elif granularity == 'week': sql_trunc_unit = 'week'
    else: sql_trunc_unit = 'month'
        
    topics_to_fetch = expand_topics_with_subtopics(selected_main_topics)

    group_date_col = func.date_trunc(sql_trunc_unit, models.Review.date).cast(Date).label("group_date")
    
    # Получаем сырые данные, сгруппированные по дате
    base_query = db.query(
        group_date_col,
        models.ReviewTopicLink.id,
        models.Topic.name,
        models.ReviewTopicLink.sentiment
    ).join(models.Review).join(models.Topic)

    base_query = base_query.filter(models.Topic.name.in_(topics_to_fetch))
    
    if sources:
        source_list = [s.strip() for s in sources.split(',')]
        base_query = base_query.filter(models.Review.source.in_(source_list))
    
    if start_date and end_date:
        base_query = base_query.filter(func.cast(models.Review.date, Date).between(start_date, end_date))

    results = base_query.order_by("group_date").all()

    # Агрегируем в Python
    data = {}
    processed_links_per_date = {}

    for group_date, review_link_id, topic_name, sentiment in results:
        if not group_date: continue
        
        # Инициализируем словари для новой даты
        data.setdefault(group_date, {"positive": 0, "neutral": 0, "negative": 0})
        processed_links_per_date.setdefault(group_date, set())

        # Проверяем, что этот отзыв еще не был учтен для этой даты
        if review_link_id in processed_links_per_date[group_date]:
            continue

        parent_topics = postprocessing.subtopic_to_topics_map.get(topic_name, [])
        if any(pt in selected_main_topics for pt in parent_topics):
            data[group_date][sentiment.lower()] += 1
            processed_links_per_date[group_date].add(review_link_id)

    raw_categories_dates = sorted(data.keys())
    formatted_categories = [format_date_label(d, granularity) for d in raw_categories_dates]
    
    return data, raw_categories_dates, formatted_categories


@app.get("/api/dynamics")
async def get_dynamics_chart_data(
    products: str | None = None,
    sources: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = 'month',
    db: Session = Depends(get_db)
):
    """Эндпоинт для графика долей (%)"""
    data, raw_categories_dates, formatted_categories = create_dynamics_data(products, sources, start_date, end_date, granularity, db)

    series_data = {s: [] for s in ['positive', 'negative', 'neutral']}
    for date_key in raw_categories_dates:
        total = sum(data.get(date_key, {}).values())
        for sentiment in series_data:
            count = data.get(date_key, {}).get(sentiment, 0)
            series_data[sentiment].append((count / total) * 100 if total > 0 else 0)
            
    colors = {'positive': '#00875A', 'negative': '#DE350B', 'neutral': '#FFA500'}
    names = {'positive': 'Позитивные', 'negative': 'Негативные', 'neutral': 'Нейтральные'}
    # Упорядочиваем легенду: Позитивные, Нейтральные, Негативные
    sentiments_order = ['negative', 'neutral', 'positive']

    chart_data = []
    for sentiment in sentiments_order:
        chart_data.append({
            'x': formatted_categories,
            'y': series_data[sentiment],
            'name': names[sentiment],
            'type': 'scatter',
            'mode': 'lines',
            'stackgroup': 'one',
            'line': {'width': 0.5, 'color': colors[sentiment]},
            'fillcolor': colors[sentiment]
        })
        
    return {"data": chart_data}


@app.get("/api/dynamics_stacked_bar")
async def get_dynamics_stacked_bar(
    products: str | None = None,
    sources: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = 'month',
    db: Session = Depends(get_db)
):
    """Эндпоинт для графика количества (stacked bar)"""
    data, raw_categories_dates, formatted_categories = create_dynamics_data(products, sources, start_date, end_date, granularity, db)
        
    # Упорядочиваем легенду: Позитивные, Нейтральные, Негативные
    sentiments_order = ['negative', 'neutral', 'positive']
    colors = {'positive': '#00875A', 'negative': '#DE350B', 'neutral': '#FFA500'}
    names = {'positive': 'Позитивные', 'negative': 'Негативные', 'neutral': 'Нейтральные'}

    chart_data = []
    for sentiment in sentiments_order:
        counts = [data.get(date_key, {}).get(sentiment, 0) for date_key in raw_categories_dates]
        chart_data.append({
            'name': names[sentiment],
            'x': formatted_categories,
            'y': counts,
            'type': 'bar',
            'marker': {'color': colors[sentiment]}
        })

    return {"data": chart_data}


@app.get("/api/products_list")
async def get_products_list(): # <-- Убираем зависимость от базы (db)
    """Эндпоинт для списка продуктов"""
    # Возвращаем отсортированный список основных тем из postprocessing.py
    return sorted(postprocessing.main_topics)


@app.get("/api/sources_list")
async def get_sources_list(db: Session = Depends(get_db)):
    """Эндпоинт для списка источников отзывов."""
    sources_query = db.query(models.Review.source).distinct().order_by(models.Review.source)
    # Возвращаем только непустые значения
    return [s.source for s in sources_query.all() if s.source]