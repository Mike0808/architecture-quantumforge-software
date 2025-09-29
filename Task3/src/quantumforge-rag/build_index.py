import os
import json
from loguru import logger
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid

# === Настройка логирования Loguru ===
logger.add("logs/build_index.log", rotation="10 MB", retention="7 days", level="INFO", enqueue=True)

# === Настройки кэширования ===
USE_CACHE = True  # <-- флаг: True = проверять кэш, False = игнорировать
CACHE_DIR = "cache_chunks"
os.makedirs(CACHE_DIR, exist_ok=True)

# === 1. Эмбеддинг-модель ===
model_name = "sentence-transformers/all-MiniLM-L6-v2"
logger.info(f"Загружаем модель эмбеддингов: {model_name}")
embedder = SentenceTransformer(model_name)

# === 2. Подключение к Qdrant ===
qdrant = QdrantClient(host="localhost", port=6333, timeout=60)  # таймаут 60 секунд
collection_name = "company_docs"
qdrant_collections = [c.name for c in qdrant.get_collections().collections]
if collection_name not in qdrant_collections:
    logger.info(f"Создаём коллекцию Qdrant: {collection_name}")
    qdrant.recreate_collection(
        collection_name=collection_name,
        vectors_config={"size": embedder.get_sentence_embedding_dimension(), "distance": "Cosine"}
    )

# === 3. Настройка сплиттера текста ===
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    length_function=len
)

# === 4. Обработка файлов ===
docs_dir = "knowledge_base"
points = []
file_count = 0
chunk_count = 0
cwd = os.getcwd()
print(cwd)
for filename in os.listdir(docs_dir):
    if not filename.endswith(".txt"):
        continue

    filepath = os.path.join(docs_dir, filename)
    cache_file_prefix = os.path.join(CACHE_DIR, filename)

    # --- Проверка кэша ---
    if USE_CACHE:
        cached_files = [f for f in os.listdir(CACHE_DIR) if f.startswith(filename)]
        if cached_files:
            logger.info(f"Файл {filename} уже обработан, загружаем чанки из кэша")
            for cf in cached_files:
                with open(os.path.join(CACHE_DIR, cf), "r", encoding="utf-8") as f:
                    chunk_data = json.load(f)
                points.append(PointStruct(
                    id=chunk_data["id"],
                    vector=chunk_data["vector"],
                    payload=chunk_data["payload"]
                ))
                chunk_count += 1
            continue

    # --- Чтение и разбиение файла ---
    file_count += 1
    logger.info(f"Читаем файл: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = splitter.split_text(text)
    logger.info(f"Разбили на {len(chunks)} чанков")

    # --- Генерация эмбеддингов и кэширование ---
    for i, chunk in enumerate(chunks):
        vector = embedder.encode(chunk).tolist()
        point_id = f"{filename}_{i}"

        chunk_data = {
            "id": str(uuid.uuid4()),
            "vector": vector,
            "payload": {
                "source": filepath,
                "chunk_id": i,
                "text": chunk,
                "title": filename,
            }
        }

        # Сохраняем каждый чанк в кэш
        with open(f"{cache_file_prefix}_{i}.json", "w", encoding="utf-8") as f:
            json.dump(chunk_data, f, ensure_ascii=False, indent=2)

        points.append(PointStruct(
            id=point_id,
            vector=vector,
            payload=chunk_data["payload"]
        ))

    chunk_count += len(chunks)

# === 5. Загрузка в Qdrant ===
BATCH_SIZE = 500  # можно уменьшить при таймаутах
if points:
    logger.info(f"Загружаем {len(points)} чанков в коллекцию '{collection_name}'")
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]
        qdrant.upsert(collection_name=collection_name, points=batch)
        logger.info(f"Загружено {len(batch)} чанков ({i+len(batch)}/{len(points)})")

logger.info(f"Обработано файлов: {file_count}, всего чанков: {chunk_count}")
logger.success("Генерация и загрузка эмбеддингов завершена")
