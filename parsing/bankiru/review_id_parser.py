import csv
import time
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import random
import os

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
OUTPUT_CSV_PATH = 'banki_ru_all_reviews_ids.csv' # Итоговый файл для всех услуг
START_PAGE = 1 # С какой страницы начинать парсинг для КАЖДОЙ услуги
END_PAGE = -1  # Конечная страница. Установите -1, чтобы парсить до самого конца автоматически.

# --- СПИСОК УСЛУГ ДЛЯ ПАРСИНГА ---
# Чтобы пропустить услугу, просто закомментируйте строку (поставьте # в начале)
SERVICES = {
    'Дебетовая карта': 'https://www.banki.ru/services/responses/bank/gazprombank/product/debitcards/',
    'Кредитная карта': 'https://www.banki.ru/services/responses/bank/gazprombank/product/creditcards/',
    'Ипотека': 'https://www.banki.ru/services/responses/bank/gazprombank/product/hypothec/',
    'Автокредит': 'https://www.banki.ru/services/responses/bank/gazprombank/product/autocredits/',
    'Потребительский кредит': 'https://www.banki.ru/services/responses/bank/gazprombank/product/credits/',
    'Реструктуризация / Рефинансирование': 'https://www.banki.ru/services/responses/bank/gazprombank/product/restructing/',
    'Вклад': 'https://www.banki.ru/services/responses/bank/gazprombank/product/deposits/',
    'Денежный перевод': 'https://www.banki.ru/services/responses/bank/gazprombank/product/transfers/',
    'Дистанционное обслуживание физических лиц': 'https://www.banki.ru/services/responses/bank/gazprombank/product/remote/',
    'Другое (физ. лица)': 'https://www.banki.ru/services/responses/bank/gazprombank/product/other/',
    'Мобильное приложение': 'https://www.banki.ru/services/responses/bank/gazprombank/product/mobile_app/',
    'Обслуживание физических лиц': 'https://www.banki.ru/services/responses/bank/gazprombank/product/individual/',
}

# --- НАСТРОЙКИ ЗАПРОСА ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'X-Requested-With': 'XMLHttpRequest',
    'X-Widget-Name': 'legacy-widget',
}

# При попытке парсинга и при дополнительном анализе сайта выснилось:
# Непроверенные отзывы дублируются в разных услугах; на сайте в таком случае
# на странице отзыва указана первая услуга из выпадающего меню услуг на сайте
# (мы парсим отзывы по услугам в этом же порядке). Поэтому в ходе парсинга
# мы проверяем, что ID отзыва не был уже записан в файл.
scraped_ids = set()
total_ids_scraped = 0

# --- РЕШЕНИЕ ПРОБЛЕМЫ С ЗАГОЛОВКОМ (№2) И ЗАГРУЗКА УЖЕ СОБРАННЫХ ID ---
# Проверяем, существует ли файл, и если да, читаем все ID оттуда, чтобы избежать дублей при дозаписи
file_exists = os.path.isfile(OUTPUT_CSV_PATH)
if file_exists and os.path.getsize(OUTPUT_CSV_PATH) > 0:
    try:
        with open(OUTPUT_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Пропускаем заголовок
            next(reader, None) 
            for row in reader:
                if row: # Проверяем, что строка не пустая
                    scraped_ids.add(row[0])
        print(f"Обнаружен существующий файл. Загружено {len(scraped_ids)} уникальных ID для проверки дубликатов.")
    except Exception as e:
        print(f"Не удалось прочитать существующий файл: {e}. Начинаем с нуля.")
        scraped_ids = set()


try:
    with open(OUTPUT_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Если файл был пуст (или его не было), записываем заголовок
        if not file_exists or os.path.getsize(OUTPUT_CSV_PATH) == 0:
            writer.writerow(['id', 'service_name'])

        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Внешний цикл по всем услугам
        for service_name, base_url in SERVICES.items():
            tqdm.write(f"\n{'='*50}\n--- Начинаем парсинг услуги: '{service_name}' (со стр. {START_PAGE}) ---\n{'='*50}")
            
            page = START_PAGE
            
            # Внутренний цикл по страницам для текущей услуги
            while True:
                # Проверка на ручное ограничение количества страниц
                if END_PAGE != -1 and page > END_PAGE:
                    tqdm.write(f"Достигнут ручной лимит в {END_PAGE} страниц для услуги '{service_name}'.")
                    break

                # Формируем URL для API-запроса
                current_url = f"{base_url}?page={page}&type=all&is_ajax=1"
                
                try:
                    response = session.get(current_url, headers={'Referer': base_url})
                    response.raise_for_status()

                    html_content = response.text
                    if not html_content.strip():
                        tqdm.write(f"--- Страница {page}: получен пустой ответ. Завершаем парсинг услуги '{service_name}'. ---")
                        break

                    soup = BeautifulSoup(html_content, 'lxml')
                    
                    # --- РЕШЕНИЕ ПРОБЛЕМЫ С ДУБЛИКАТАМИ (№1) ---
                    # Ищем родительские блоки каждого отзыва
                    review_blocks = soup.select('div.la8a5ef73')

                    if not review_blocks:
                        tqdm.write(f"--- Страница {page}: не найдено блоков с отзывами. Завершаем парсинг услуги '{service_name}'. ---")
                        break
                    
                    new_ids_on_page = 0
                    for block in review_blocks:
                        # В каждом блоке ищем только ОДНУ ссылку, ведущую на отзыв
                        link = block.select_one('a[href*="/services/responses/bank/response/"]')
                        if not link:
                            continue
                        
                        href = link.get('href')
                        if href:
                            try:
                                review_id = href.strip('/').split('/')[-1]
                                # Проверяем, что ID - это число и что мы его еще не записывали
                                if review_id.isdigit() and review_id not in scraped_ids:
                                    writer.writerow([review_id, service_name])
                                    scraped_ids.add(review_id)
                                    new_ids_on_page += 1
                                    total_ids_scraped += 1
                            except (IndexError, ValueError):
                                continue
                    
                    tqdm.write(f"Страница {page} ('{service_name}'): Найдено и записано {new_ids_on_page} новых ID. Всего в файле: {len(scraped_ids)}")

                    # Если на странице не нашлось НИ ОДНОГО нового ID (хотя блоки были), возможно это конец
                    if new_ids_on_page == 0 and page > START_PAGE:
                         tqdm.write(f"--- На странице {page} не найдено новых уникальных ID. Завершаем услугу '{service_name}'.")
                         break

                    page += 1
                    time.sleep(random.uniform(0.5, 1.5))

                except requests.exceptions.HTTPError as e:
                    tqdm.write(f"!!! HTTP Ошибка на странице {page}: {e}. Статус: {e.response.status_code}")
                    if e.response.status_code in [403, 429, 503]:
                        tqdm.write("Сервер временно недоступен или блокирует запросы. Ждем 60 секунд...")
                        time.sleep(60)
                    else:
                        time.sleep(10)
                except requests.exceptions.RequestException as e:
                    tqdm.write(f"!!! Ошибка сети на странице {page}: {e}. Ждем 20 секунд.")
                    time.sleep(20)

except Exception as e:
    print(f"Произошла критическая ошибка: {e}")

finally:
    print(f"\n--- ПАРСИНГ ЗАВЕРШЕН! ---")
    print(f"Результаты сохранены в файле: {OUTPUT_CSV_PATH}")
    print(f"Общее количество уникальных ID в файле: {len(scraped_ids)}")