import os
import sys
import time

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, inspect
import pandas as pd
import numpy as np
import gdown

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .database import engine, Base
from .models import Review, Topic, ReviewTopicLink


# --- Логика ожидания базы ---
# Иногда healthcheck проходит, а база все еще не готова на 100%.
def wait_for_db():
    max_retries = 10
    retry_delay = 10
    for i in range(max_retries):
        try:
            # Пытаемся создать соединение
            connection = engine.connect()
            connection.close()
            print("База данных готова!")
            return True
        except Exception as e:
            print(f"База данных не готова (попытка {i+1}/{max_retries}): {e}")
            time.sleep(retry_delay)
    print("Не удалось подключиться к базе данных после нескольких попыток.")
    return False

# Вызываем функцию ожидания перед тем, как что-либо делать
if not wait_for_db():
    exit(1) # Выходим с ошибкой, если не смогли подключиться


# --- CSV-файлы с требуемой структурой ---
REVIEWS_GDRIVE_ID =        '1-m3vO4MJtfT3tfeRwN3pTr5b7H-4bJe4'
TOPICS_GDRIVE_ID =         '1kl8lEPOgwrfxWkOB6gF6z-e9yBPodh2s'
REVIEWS_TOPICS_GDRIVE_ID = '1jf3-Zgdtumo0UhxAuE2AmpRfYlxIrgFw'

# Локальные пути, куда будут сохраняться файлы внутри контейнера
DATA_DIR = './data'
REVIEWS_CSV = os.path.join(DATA_DIR, 'reviews.csv')
TOPICS_CSV = os.path.join(DATA_DIR, 'topics.csv')
REVIEWS_TOPICS_CSV = os.path.join(DATA_DIR, 'reviews_topics.csv')


Session = sessionmaker(bind=engine)
session = Session()

# --- ПРОВЕРКА СУЩЕСТВОВАНИЯ ТАБЛИЦ ---
inspector = inspect(engine)
# Проверяем наличие одной из ключевых таблиц
if inspector.has_table("reviews"):
    print("База данных уже заполнена. Пропускаем seeding.")
    session.close()
    # Завершаем скрипт, так как делать больше нечего
    exit(0) 

# --- ЕСЛИ ТАБЛИЦ НЕТ, ЗАПУСКАЕМ ПОЛНЫЙ ПРОЦЕСС ---
print("Таблицы не найдены. Запускаем процесс заполнения базы данных...")

try:
    # print("Удаляем старые таблицы...")
    # session.execute(text("DROP TABLE IF EXISTS reviews_topics CASCADE;"))
    # session.execute(text("DROP TABLE IF EXISTS topics CASCADE;"))
    # session.execute(text("DROP TABLE IF EXISTS reviews CASCADE;"))
    # session.commit()
    # print("Старые таблицы удалены.")

    print("Создаем новые таблицы...")
    Base.metadata.create_all(bind=engine)
    print("Новые таблицы созданы.")

    # --- 4. СКАЧИВАНИЕ ФАЙЛОВ ---
    print("Скачивание файлов из Google Drive...")
    os.makedirs(DATA_DIR, exist_ok=True) # Создаем папку /data, если ее нет

    gdown.download(id=REVIEWS_GDRIVE_ID, output=REVIEWS_CSV, quiet=False)
    print(f"Скачан {REVIEWS_CSV}")

    gdown.download(id=TOPICS_GDRIVE_ID, output=TOPICS_CSV, quiet=False)
    print(f"Скачан {TOPICS_CSV}")

    gdown.download(id=REVIEWS_TOPICS_GDRIVE_ID, output=REVIEWS_TOPICS_CSV, quiet=False)
    print(f"Скачан {REVIEWS_TOPICS_CSV}")
    print("Все файлы скачаны успешно.")

    df_reviews = pd.read_csv(REVIEWS_CSV)
    df_topics = pd.read_csv(TOPICS_CSV)
    df_reviews_topics = pd.read_csv(REVIEWS_TOPICS_CSV)
    
    # --- Заполнение ---

    # topics
    print("Заполняем 'topics' таблицу...")
    session.bulk_insert_mappings(Topic, df_topics.to_dict(orient='records'))
    print(f"Заполнено {len(df_topics)} topics.")

    # reviews
    print("Заполняем 'reviews' таблицу...")
    df_reviews_cleaned = df_reviews.replace({np.nan: None})
    df_reviews_cleaned['date'] = pd.to_datetime(df_reviews_cleaned['date'], format='%Y-%m-%d')
    print(df_reviews_cleaned)
    session.bulk_insert_mappings(Review, df_reviews_cleaned.to_dict(orient='records'))
    print(f"Заполнено {len(df_reviews)} reviews.")

    # reviews_topics
    print("Заполняем 'reviews_topics' table...")
    session.bulk_insert_mappings(ReviewTopicLink, df_reviews_topics.to_dict(orient='records'))
    print(f"Заполнено {len(df_reviews_topics)} review-topic links.")
    session.commit()
    print("\nБаза данных успешно заполнена!")

except Exception as e:
    print(f"\nПроизошла ошибка: {e}")
    session.rollback()
finally:
    session.close()