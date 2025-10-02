import csv
import time
# Функции для парсинга дат были убраны в вашем коде, поэтому я их тоже убрал.

# Импорты для Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from tqdm import tqdm

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
INPUT_CSV_PATH = '../../datasets/sravni_ru/review_ids.csv' # Убедитесь, что это правильное имя файла с ID
OUTPUT_CSV_PATH = '../../datasets/sravni_ru/sravni_dataset.csv' # Новое имя для итогового файла

BASE_URL = 'https://www.sravni.ru/bank/gazprombank/otzyvy/{}/'

# Установите -1 для обработки всех ID
TEST_LIMIT = -1

# --- ОСНОВНОЙ СКРИПТ ---
try:
    with open(INPUT_CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader) # Пропускаем заголовок
        all_review_ids = [row[0] for row in reader]
except FileNotFoundError:
    print(f"Ошибка: Входной файл '{INPUT_CSV_PATH}' не найден.")
    exit()

ids_to_process = all_review_ids[:TEST_LIMIT] if TEST_LIMIT > 0 else all_review_ids
print(f"--- Запускаем обработку {len(ids_to_process)} отзывов в фоновом режиме ---")

# --- Настройка опций Chrome ---
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--headless=new') 
options.add_argument('--window-size=1920,1080') 
options.add_experimental_option('excludeSwitches', ['enable-logging'])

try:
    driver = webdriver.Chrome(options=options)
except Exception as e:
    print(f"Не удалось запустить WebDriver: {e}")
    exit()

# --- Потоковая запись в CSV ---
try:
    with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # ИЗМЕНЕНИЕ: Добавляем новые колонки в заголовок
        writer.writerow(['review_id', 'date', 'review_text', 'topic', 'subtopic'])
        
        success_count = 0
        
        # Основной цикл парсинга
        for review_id in tqdm(ids_to_process):
            url = BASE_URL.format(review_id)
            try:
                driver.get(url)
                wait = WebDriverWait(driver, 10)

                main_review_selector = f'div[data-id="{review_id}"]'
                main_review_block = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, main_review_selector)))
                
                # --- ВАШ КОД ПОИСКА ДАТЫ (БЕЗ ИЗМЕНЕНИЙ) ---
                date_elements = main_review_block.find_elements(By.CSS_SELECTOR, 'div[class*="h-color-D30"]')
                if not date_elements:
                    raise NoSuchElementException("Элемент с датой не найден.")
                
                if date_elements[0].text.strip() == ", клиент Сравни":
                    date_element = date_elements[1]
                else:
                    date_element = date_elements[0]

                # --- ВАШ КОД ПОИСКА ТЕКСТА (БЕЗ ИЗМЕНЕНИЙ) ---
                text_element = main_review_block.find_element(By.CSS_SELECTOR, 'div[class*="review-card_text"]')

                # --- ИСПРАВЛЕНИЕ: ДОБАВЛЕНА НАДЕЖНАЯ ЛОГИКА ПОИСКА ТЕМЫ/ПОДТЕМЫ ---
                topic = None
                subtopic = None
                try:
                    # 1. Находим блок, который идет СРАЗУ ПОСЛЕ блока с текстом отзыва
                    #    Он содержит и название банка, и тему, и подтему
                    footer_container = main_review_block.find_element(By.XPATH, './/div[contains(@class, "review-card_text")]/following-sibling::div[1]')

                    # 2. Находим внутри него все ссылки и div'ы
                    all_candidates = footer_container.find_elements(By.XPATH, './a | ./div')
                    all_candidates = [i.text.strip() for i in all_candidates][1:]
                    if len(all_candidates) == 2:
                        topic = all_candidates[0]
                        subtopic = all_candidates[1]
                    else:
                        topic = all_candidates[0]

                except NoSuchElementException:
                    # Если этого блока нет, значит нет и темы/подтемы. Это нормально.
                    pass

                # try:
                #     stars = driver.find_elements(By.CSS_SELECTOR, "[data-qa='Star']")
                #     filled_stars = len([star for star in stars if 'stroke="currentColor"' in star.get_attribute('outerHTML')])
                #     print(filled_stars)
                # except:
                #     review_data['Оценка'] = None

                # --- Извлечение данных и запись ---
                raw_date_str = date_element.text.strip()
                review_text = text_element.text.strip()
                
                # Записываем строку со всеми данными
                writer.writerow([review_id, raw_date_str, review_text, topic, subtopic])
                success_count += 1

            except TimeoutException:
                tqdm.write(f"  > Ошибка: не удалось найти главный блок для ID {review_id} за 10 секунд.")
            except NoSuchElementException:
                tqdm.write(f"  > Ошибка: внутри блока для ID {review_id} не найден текст или дата.")
            except Exception as e:
                tqdm.write(f"  > Произошла непредвиденная ошибка при обработке ID {review_id}: {e}")
            
            time.sleep(1) 

finally:
    if 'driver' in locals() and driver:
        driver.quit()
    
    print(f"\n--- ГОТОВО! ---")
    print(f"Результаты сохранены в файле: {OUTPUT_CSV_PATH}")