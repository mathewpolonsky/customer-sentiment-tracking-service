import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import pandas as pd
import numpy as np
import gdown

from .database import engine, Base
from .models import Review, Topic, ReviewTopicLink


# --- CSV-файлы с требуемой структурой ---
REVIEWS_GDRIVE_ID =        '1-m3vO4MJtfT3tfeRwN3pTr5b7H-4bJe4'
TOPICS_GDRIVE_ID =         '1PWHPBaLbtN0TCFtyIk5oP851ULLLZ-XM'
REVIEWS_TOPICS_GDRIVE_ID = '10NAfgErhwtU-R6--lC26VjQX1XXQkKMB'

# Локальные пути, куда будут сохраняться файлы внутри контейнера
DATA_DIR = './data'
REVIEWS_CSV = os.path.join(DATA_DIR, 'reviews.csv')
TOPICS_CSV = os.path.join(DATA_DIR, 'topics.csv')
REVIEWS_TOPICS_CSV = os.path.join(DATA_DIR, 'reviews_topics.csv')

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

Session = sessionmaker(bind=engine)
session = Session()

try:
    print("Удаляем старые таблицы...")
    session.execute(text("DROP TABLE IF EXISTS reviews_topics CASCADE;"))
    session.execute(text("DROP TABLE IF EXISTS topics CASCADE;"))
    session.execute(text("DROP TABLE IF EXISTS reviews CASCADE;"))
    session.commit()
    print("Старые таблицы удалены.")

    print("Создаем новые таблицы...")
    Base.metadata.create_all(bind=engine)
    print("Новые таблицы созданы.")

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
    df_reviews_to_seed = df_reviews_cleaned.rename(columns={
        'reviewId': 'id', 
        'idSiteSpecific': 'site_specific_id',
        'topic': 'source_topic',
        'subtopic': 'source_subtopic'
    })
    df_reviews_to_seed['date'] = pd.to_datetime(df_reviews_to_seed['date'], format='%Y-%m-%d')
    print(df_reviews_to_seed)
    
    session.bulk_insert_mappings(Review, df_reviews_to_seed.to_dict(orient='records'))
    print(f"Заполнено {len(df_reviews)} reviews.")

    # reviews_topics
    print("Заполняем 'reviews_topics' table...")
    df_reviews_topics_to_seed = df_reviews_topics.rename(columns={
        'reviewId': 'review_id',
        'topicId': 'topic_id'
    })
    session.bulk_insert_mappings(ReviewTopicLink, df_reviews_topics_to_seed.to_dict(orient='records'))
    print(f"Заполнено {len(df_reviews_topics)} review-topic links.")
    
    session.commit()
    print("\nБаза данных успешно заполнена!")

except Exception as e:
    print(f"\nПроизошла ошибка: {e}")
    session.rollback()
finally:
    session.close()