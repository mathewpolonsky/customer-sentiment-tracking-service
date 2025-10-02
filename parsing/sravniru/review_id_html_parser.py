from bs4 import BeautifulSoup
import csv

# --- Настройки ---
html_file_path = 'Отзывы о Газпромбанке — 4788 отзывов клиентов, решено 706 проблем.html'
csv_file_path = '../../datasets/sravni_ru/review_ids.csv' # Имя файла, в который мы будем сохранять ID

try:
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'lxml')

    # --- ШАГ 1: Находим все теги <div>, у которых есть атрибут 'data-id' ---
    # Это именно то, что показано на вашем скриншоте.
    # Ваш самый первый код был почти верным, нужно было лишь поменять 'data-review-id' на 'data-id'
    review_blocks = soup.find_all('div', {'data-id': True})

    if not review_blocks:
        print("Не найдено ни одного блока <div data-id=...>. Проверьте, что HTML-файл сохранен полностью.")
    else:
        print(f"Найдено {len(review_blocks)} отзывов в тегах <div>.")

        # --- ШАГ 2: Извлекаем ID и записываем в CSV ---
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['review_id'])  # Заголовок колонки

            # Проходим по всем найденным блокам
            for block in review_blocks:
                # Извлекаем значение атрибута 'data-id'.
                # Доступ к атрибутам, содержащим дефис, осуществляется как к ключу словаря.
                review_id = block['data-id']
                writer.writerow([review_id])

        print(f"Успешно! Все {len(review_blocks)} ID сохранены в файл: {csv_file_path}")

except FileNotFoundError:
    print(f"Ошибка: Файл '{html_file_path}' не найден.")
except Exception as e:
    print(f"Произошла непредвиденная ошибка: {e}")