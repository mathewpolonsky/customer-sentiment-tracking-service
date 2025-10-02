import csv
import time
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import random
import os
import json

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
INPUT_CSV_PATH = 'banki_ru_all_reviews_ids.csv'  # Файл с ID, который мы получили
OUTPUT_CSV_PATH = 'reviews_data.csv'                # Итоговый файл с данными отзывов

# --- НАСТРОЙКИ ЗАПРОСА ---
REVIEW_URL_TEMPLATE = "https://www.banki.ru/services/responses/bank/response/{review_id}/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
}

# --- ОСНОВНОЙ КОД ---

# 1. Считываем все ID вместе с названиями услуг
reviews_to_scrape = []
try:
    with open(INPUT_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        reviews_to_scrape = [(row[0], row[1]) for row in reader if row]
    print(f"Найдено {len(reviews_to_scrape)} пар (ID, Услуга) для парсинга в файле {INPUT_CSV_PATH}")
except FileNotFoundError:
    print(f"Ошибка: Файл с ID '{INPUT_CSV_PATH}' не найден.")
    exit()

# 2. Проверяем, какие ID уже были спарсены
processed_ids = set()
file_exists = os.path.isfile(OUTPUT_CSV_PATH)
if file_exists and os.path.getsize(OUTPUT_CSV_PATH) > 0:
    try:
        with open(OUTPUT_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row:
                    processed_ids.add(row[0])
        print(f"Обнаружен существующий файл. Загружено {len(processed_ids)} уже обработанных ID.")
    except Exception as e:
        print(f"Не удалось прочитать существующий файл: {e}. Начинаем с чистого листа.")

# 3. Основной цикл парсинга
total_new_reviews = 0
try:
    with open(OUTPUT_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(OUTPUT_CSV_PATH) == 0:
            writer.writerow(['review_id', 'date', 'rating', 'service_name', 'review_text'])

        session = requests.Session()
        session.headers.update(HEADERS)

        for review_id, service_name in tqdm(reviews_to_scrape, desc="Парсинг отзывов"):
            if review_id in processed_ids:
                continue
            
            current_url = REVIEW_URL_TEMPLATE.format(review_id=review_id)
            
            try:
                response = session.get(current_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')

                # --- Извлекаем данные ---
                date_element = soup.select_one('div.l51115aff > span.l10fac986')
                date = date_element.get_text(strip=True) if date_element else 'ДАТА НЕ НАЙДЕНА'

                # --- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Универсальный селектор для ОЦЕНКИ ---
                # Ищем любой div, класс которого СОДЕРЖИТ 'rating-grade',
                # чтобы находить и обычные, и проверенные отзывы.
                rating_element = soup.select_one('div[class*="rating-grade"]')
                rating = rating_element.get_text(strip=True) if rating_element else 'БЕЗ ОЦЕНКИ'
                
                # Извлекаем текст отзыва
                review_text = 'ТЕКСТ НЕ НАЙДЕН'
                text_module_div = soup.select_one('div[data-module*="response-text/body"]')
                
                if text_module_div:
                    options_str = text_module_div.get('data-module-options')
                    if options_str:
                        options_json = json.loads(options_str)
                        text_html = options_json.get('text', '')
                        if text_html:
                            text_soup = BeautifulSoup(text_html, 'lxml')
                            review_text = text_soup.get_text(separator='\n', strip=True)

                # Записываем найденные данные в CSV
                writer.writerow([review_id, date, rating, service_name, review_text])
                total_new_reviews += 1
                
                tqdm.write(f"ID: {review_id} | Сервис: {service_name} | Дата: {date} | Оценка: {rating}")
                
                processed_ids.add(review_id)
                time.sleep(random.uniform(0.4, 1.2))

            except requests.exceptions.HTTPError as e:
                tqdm.write(f"!!! HTTP Ошибка для ID {review_id} (Статус: {e.response.status_code}). URL: {current_url}")
                writer.writerow([review_id, 'HTTP ERROR', e.response.status_code, service_name, str(e)])
                time.sleep(5)
            except Exception as e:
                tqdm.write(f"!!! Непредвиденная ошибка для ID {review_id}: {e}")
                writer.writerow([review_id, 'PARSE ERROR', 'N/A', service_name, str(e)])

except KeyboardInterrupt:
    print("\nПарсинг прерван пользователем.")
except Exception as e:
    print(f"\nПроизошла критическая ошибка: {e}")

finally:
    print(f"\n--- ПАРСИНГ ЗАВЕРШЕН! ---")
    print(f"Результаты сохранены в файле: {OUTPUT_CSV_PATH}")
    print(f"Всего добавлено новых отзывов за сессию: {total_new_reviews}")
    print(f"Общее количество уникальных отзывов в файле: {len(processed_ids)}")