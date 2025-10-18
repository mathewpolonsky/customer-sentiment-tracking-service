import asyncio
import aiohttp
import time
import json
import pandas as pd
from typing import List, Dict, Any
from tqdm.asyncio import tqdm
print = tqdm.write


SYSTEM_PROMPT = """\
Проанализируй отзыв клиента Газпромбанка (ГПБ) и определи:
1. Упоминаемые тем ("topic") из списка допустимых тем;
2. Тональность ("sentiment") для каждой темы: positive/negative/neutral.

ПРАВИЛА:
- Тональность: `neutral` указывается тогда, когда тема упомянута как факт, без эмоциональной окраски;
- Не выдумывай темы: Если в отзыве нет явного упоминания продукта или услуги, не включай его;
- Если темы нет: Если невозможно определить ни одну тему, верни пустой массив [];
- Темы: Используй ТОЛЬКО следующий список тем и подтем. Не добавляй новые темы;
- Уникальность тем: Одна тема может встречаться только один раз.

ДОПУСТИМЫЕ ТЕМЫ:
- Офисное обслуживание (обслуживание в отделениях банка)
- Дистанционное обслуживание (звонки, чаты, онлайн-консультации и подобное)
- Банкоматы
- Курьерская доставка карт
- Обмен валют
- Дебетовые карты (включая подтемы: Денежные переводы, Карта UnionPay, Умная дебетовая карта «Мир», Премиальная карта Mir Supreme)
- Кредитные карты (включая подтемы: Кредитная карта 180 дней Премиум)
- Кредиты (включая подтемы: Кредит наличными, Кредит наличными под залог недвижимости, Кредит под залог автомобиля)
- Рефинансирование/Реструктуризация (включая подтемы: Рефинансирование кредитов, Реструктуризация кредитов, Рефинансирование ипотеки, Реструктуризация ипотеки)
- Автокредиты
- Ипотека
- Страховые и сервисные продукты
- Вклады (включая подтемы: Вклад «Копить», Вклад «В Плюсе», Вклад «Новые деньги»)
- Накопительные счета (включая подтемы: Накопительный счёт «Ежедневная выгода», Накопительный счёт «Ежедневный процент», Накопительный счёт «Премиум»)
- Акции и бонусы (включая подтемы: Газпром Бонус, Газпромбанк Привилегии, Кэшбэк, Акции, Программы лояльности)
- Газпромбанк Премиум (включая подтемы: Персональный менеджер, Консьерж-сервис, Премиальное обслуживание)
- Мобильное приложение
- Другие услуги банка (включая подтемы: Газпромбанк Travel (покупка авиабилетов/отелей), Gazprom Pay (оплата телефоном), GorodPay (оплата общественного транспорта), Инвестиционные продукты, Брокерские услуги, Депозитарные услуги, Аренда сейфовых ячеек)

Примеры:
Отзыв: "В отделении грубо обслужили, но мобильное приложение удобное"
[
{"topic": "Офисное обслуживание", "sentiment": "negative"},
{"topic": "Мобильное приложение", "sentiment": "positive"}
]

Отзыв: "Курьер не пришёл на встречу. По телефону не смогли помочь."
[
{"topic": "Курьерская доставка карт", "sentiment": "negative"},
{"topic": "Дистанционное обслуживание", "sentiment": "negative"}
]

Отзыв: "Оформил Премиальную карту Mir Supreme через приложение"
[
{"topic": "Премиальная карта Mir Supreme", "sentiment": "neutral"},
{"topic": "Дебетовые карты", "sentiment": "neutral"},
{"topic": "Газпромбанк Премиум", "sentiment": "neutral"},
{"topic": "Мобильное приложение", "sentiment": "neutral"}
]

Отзыв: "Пользуюсь Газпромбанк Travel для бронирования отелей и Gazprom Pay для оплаты"
[
{"topic": "Другие услуги банка", "sentiment": "neutral"},
{"topic": "Газпромбанк Travel", "sentiment": "neutral"},
{"topic": "Gazprom Pay", "sentiment": "neutral"}
]

Проанализируй следующий отзыв:
"""

def validate_response_structure(pairs: list) -> bool:
    """Проверяет что ответ соответствует требуемой структуре"""
    try:
        if not isinstance(pairs, list):
            return False
            
        for pair in pairs:
            # print(pair)
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


async def main_async():
    df = pd.read_csv("data/reviews_our_time.csv") #.sample(1000, random_state=24) #.iloc[:100]
    
    # model_name = "JosephThePatrician/gemma3-270m-it-reviews-v3"
    # model_name = "JosephThePatrician/qwen3_0.6b-reviews-fine-tune-v2"
    # model_name = "JosephThePatrician/qwen3_0.6b-reviews-fine-tune-v3"
    model_name = "JosephThePatrician/qwen3_0.6b-reviews-fine-tune-v4"
    # model_name = "JosephThePatrician/qwen2.5_0.5b-reviews-fine-tune-v1"

    
    turn_qwen_thinking_off = ("qwen3" in model_name)
    
    save_path = f"data/inference/inference_results_{model_name.split('/')[-1]}.json"
    max_connections = 400
    max_retries = 10
    
    reviews = df["review_text"].tolist()
    review_ids = df["id"].tolist()
    
    start_total = time.time()
    results = []
    failed_requests = []
    
    # Семафор для ограничения concurrent запросов
    semaphore = asyncio.Semaphore(max_connections)
    
    async def send_request(session, review, review_id, index, max_retries=3):
        async with semaphore:
            for attempt in range(max_retries + 1):

                if (attempt == (max_retries)):  # Последняя попытка
                    print(f"Слишком много попыток для reviewId {review_id}, попытка {attempt + 1}. Пропускаем.")
                    failed_requests.append({
                        "reviewId": review_id,
                        "index": index,
                        "error": "too many attempts failed",
                        "success": False,
                        "attempts": attempt + 1
                    })
                    results.append({
                        "reviewId": review_id,
                        "index": index,
                        "success": False,
                        "topic_sentiment_pairs": [],
                        "attempts": attempt + 1,
                    })
                    return
                
                try:
                    request_start = time.time()
                    payload = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": review + " /no_think" * turn_qwen_thinking_off}
                        ],
                        "temperature": 0.1,
                        # "repetition_penalty" : 0.99,
                        "max_tokens" : 150,
                    }
                    
                    async with session.post(
                        "http://192.168.0.193:8100/v1/chat/completions",
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        response_data = await response.json()
                        # print(str(response_data))
                        request_end = time.time()
                        
                        if response.status == 200:
                            response_content = response_data.get('choices', [{}])[0].get('message', {}).get('content')
                            
                            # print(str(response_content))
                            
                            # Пытаемся распарсить JSON ответ
                            try:
                                response_content = response_content.replace("<think>\n\n</think>", "").strip()
                                # print(str(response_content))
                                parsed_response = eval(response_content)
                                
                                # Проверяем структуру ответа
                                if validate_response_structure(parsed_response):
                                    results.append({
                                        "reviewId": review_id,
                                        "index": index,
                                        "time": request_end - request_start,
                                        "success": True,
                                        "topic_sentiment_pairs": parsed_response,
                                        "attempts": attempt + 1
                                    })
                                    return
                                else:
                                    # print(f"Неверная структура ответа для reviewId {review_id}, попытка {attempt + 1}")
                                    continue  # Пробуем еще раз
                                    
                            except SyntaxError:
                                # print(f"Невалидный JSON для reviewId {review_id}, попытка {attempt + 1}\n{response_content[:300]}")
                                continue  # Пробуем еще раз
                                
                        else:
                            print(f"HTTP ошибка {response.status} для reviewId {review_id}")
                            continue
                            
                except Exception as e:
                    print(f"Ошибка для reviewId {review_id}, попытка {attempt + 1}: {str(e)}")
                    await asyncio.sleep(1)  # Задержка перед повторной попыткой

    async with aiohttp.ClientSession() as session:
        tasks = [send_request(session, review, review_id, i, max_retries)
                for i, (review, review_id) in enumerate(zip(reviews, review_ids))]
        await tqdm.gather(*tasks)

    end_total = time.time()
    total_time = end_total - start_total
    
    # Сохраняем результаты в JSON файл
    output_data = {
        "metadata": {
            "total_requests": len(reviews),
            "successful_requests": len(results),
            "failed_requests": len(failed_requests),
            "total_time_seconds": total_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "results": results,
        "failed": failed_requests
    }
    
    # Сохраняем с форматированием для читаемости :cite[8]
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # Выводим статистику
    successful = [r for r in results if r['success']]
    
    print(f"Общее время: {total_time:.2f} секунд")
    print(f"Успешных запросов: {len(successful)}")
    print(f"Неудачных запросов: {len(failed_requests)}")
    print(f"Результаты сохранены в {save_path}")

    # if successful:
    #     avg_time = sum(r['time'] for r in successful) / len(successful)
    #     print(f"Среднее время на запрос: {avg_time:.2f} сек")
    #     print(f"Примерная скорость: {len(successful)/total_time:.2f} запросов/сек")

# Запуск асинхронной версии
asyncio.run(main_async())