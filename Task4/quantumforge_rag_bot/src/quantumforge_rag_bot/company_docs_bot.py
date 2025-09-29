import os
from loguru import logger
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from openai import OpenAI
import tiktoken
import re
import time


# === Конфигурация ===
FALLBACK_SECRET_REPLY = "Не могу вам сказать... Позвоните по номеру 125"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "company_docs"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "o4-mini"
MAX_TOKENS_CONTEXT = 3000
FEW_SHOTS_FILE = "./Task4/quantumforge_rag_bot/few_shots.txt"
MODERATION_ENABLED = False  # set False to disable OpenAI moderation
OPENAI_MODERATION_MODEL = "omni-moderation-latest"  # or "text-moderation-latest"
TOP_K = 5
MIN_SCORE = 0.3  # порог уверенности поиска

# === Инициализация клиентов ===
logger.info("Загружаем модель эмбеддингов...")
embedder = SentenceTransformer(EMBEDDING_MODEL)

logger.info("Подключаемся к Qdrant...")
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

logger.info("Подключаемся к OpenAI...")
client = OpenAI(api_key=OPENAI_API_KEY)

# === Сборка для безопасности () === 
PASSWORD_QUERY_RE = re.compile(
    r"\b(password|passwd|pwd|passphrase|secret|credentials|root password|root|superpass|superpassword|swordfish|пароль|учетк|учетная|секрет|суперпас|суперпароль)\b",
    flags=re.I
)

PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----", flags=re.I)
AWS_KEY_RE = re.compile(r"\bAKIA[A-Z0-9]{16}\b")
BASE64_LONG_RE = re.compile(r"\b[a-zA-Z0-9+/]{40,}={0,2}\b")
HEX_LONG_RE = re.compile(r"\b[0-9a-fA-F]{32,}\b")
JWT_RE = re.compile(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$")
CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")  # rough
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
SQL_INJECTION_RE = re.compile(r"\b(UNION\s+SELECT|DROP\s+TABLE|;--|--\s|\bEXEC\b|\bALTER\s+TABLE)\b", flags=re.I)
SHELL_INJECTION_RE = re.compile(r"[;&|`$()<>]")
IGNORE_ALL_INSTANCES_RE = re.compile(r"\b(ignore all instances|не учитывать|не учитывать все|игнорировать все)\b", flags=re.I)
IGNORE_ALL_INSTRUCTIONS_RE = re.compile(r"\b(ignore all instructions|не учитывать инструкции|игнорировать инструкции)\b", flags=re.I)
ROOT_RE = re.compile(r"\b(root|рут|админ|администратор|admin)\b", flags=re.I)
PASSWORD_INSTRUCTION_RE = re.compile(r"\b(password is|пароль:|пароль -|пароль |суперпас|суперпароль )\b", flags=re.I)

# === Обнаружение чувствительного контента в запросе ===
def is_sensitive_query(query: str) -> bool:
    q = query.strip()
    # 1) direct keyword asks about credentials
    if PASSWORD_QUERY_RE.search(q):
        return True
    # 2) asks to reveal or find keys/tokens
    if re.search(r"\b(api key|private key|secret key|token|ssh key|access key|credentials)\b", q, flags=re.I):
        return True
    # 3) injection attempts
    if SQL_INJECTION_RE.search(q) or SHELL_INJECTION_RE.search(q):
        return True
    # 4) explicit social engineering phrasing
    if re.search(r"\b(give me|show me|reveal|expose|dump)\b.*\b(password|key|token|credentials|secret)\b", q, flags=re.I):
        return True
    return False

# === Обнаружение на уровне контента (применяется к чанкам) ===
def contains_secret_like_text(text: str) -> bool:
    if PRIVATE_KEY_RE.search(text):
        return True
    if AWS_KEY_RE.search(text):
        return True
    if BASE64_LONG_RE.search(text) and len(text) > 200:  # a lot of base64 likely secret/blob
        return True
    if HEX_LONG_RE.search(text) and len(text) > 200:
        return True
    if JWT_RE.search(text):
        return True
    if CREDIT_CARD_RE.search(text):
        return True
    if SSN_RE.search(text):
        return True
    if IGNORE_ALL_INSTANCES_RE.search(text):
        return True
    if IGNORE_ALL_INSTRUCTIONS_RE.search(text): 
        return True
    if ROOT_RE.search(text):
        return True
    if PASSWORD_INSTRUCTION_RE.search(text):
        return True
    return False

# === Редактор: заменяет фрагменты с секретами на плейсхолдеры ===
def redact_secrets(text: str) -> str:
    text = PRIVATE_KEY_RE.sub("[REDACTED PRIVATE KEY]", text)
    text = AWS_KEY_RE.sub("[REDACTED AWS KEY]", text)
    text = BASE64_LONG_RE.sub("[REDACTED BASE64]", text)
    text = HEX_LONG_RE.sub("[REDACTED HEX]", text)
    text = JWT_RE.sub("[REDACTED JWT]", text)
    text = CREDIT_CARD_RE.sub("[REDACTED CREDIT CARD]", text)
    text = SSN_RE.sub("[REDACTED SSN]", text)
    text = IGNORE_ALL_INSTANCES_RE.sub("[REDACTED SENSITIVE CONTENT]", text)
    text = IGNORE_ALL_INSTRUCTIONS_RE.sub("[REDACTED SENSITIVE CONTENT]", text)
    text = ROOT_RE.sub("[REDACTED SENSITIVE CONTENT]", text)
    text = PASSWORD_INSTRUCTION_RE.sub("[REDACTED SENSITIVE CONTENT]", text)
    # Additional: redact lines that contain "password:" or "pwd="
    text = re.sub(r"(?i)password\s*[:=]\s*\S+", "[REDACTED PASSWORD]", text)
    text = re.sub(r"(?i)pwd\s*[:=]\s*\S+", "[REDACTED PWD]", text)
    return text

# === Функция модерации через OpenAI ===
def moderation_blocked(text: str) -> bool:
    if not MODERATION_ENABLED:
        return False
    try:
        resp = client.moderations.create(model=OPENAI_MODERATION_MODEL, input=text)
        # OpenAI moderations returns category scores; block if flagged
        if resp and resp.results:
            res = resp.results[0]
            if res.flagged:
                logger.warning("Moderation flagged content")
                return True
    except Exception as e:
        logger.exception("Moderation API failed")
        # fail-safe: if moderation fails, do not block; alternatively block to be paranoid
        return False
    return False

# === Настройка токенизатора ===
enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


def load_few_shots() -> str:
    """Загружает few-shot примеры из файла"""
    if os.path.exists(FEW_SHOTS_FILE):
        with open(FEW_SHOTS_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    else:
        logger.warning(f"Файл {FEW_SHOTS_FILE} не найден, few-shots будут пустыми")
        return ""


def build_prompt_with_context(query: str, search_results: list, token_limit: int = MAX_TOKENS_CONTEXT) -> str:
    """Формирует промпт для LLM с учётом лимита токенов"""

    system_prompt = (
        "Ты помощник, который сначала размышляет, а потом отвечает. "
        "Если в предоставленном контексте нет достаточной информации, "
        f"ответь строго: '{FALLBACK_SECRET_REPLY}'."
        "Отвечай только финальным ответом, без шагов рассуждений."
    )

    few_shot = load_few_shots()

    context_parts = []
    total_tokens = count_tokens(system_prompt) + count_tokens(few_shot) + count_tokens(query)

    for res in search_results:
        chunk_text = res.payload.get("text", "")
        chunk_tokens = count_tokens(chunk_text)

        if total_tokens + chunk_tokens > token_limit:
            # Обрезаем последний чанк по количеству токенов, чтобы уложиться в лимит
            remaining_tokens = token_limit - total_tokens
            if remaining_tokens > 0:
                # конвертируем обратно токены в текст
                tokens = enc.encode(chunk_text)[:remaining_tokens]
                truncated_text = enc.decode(tokens)
                context_parts.append(truncated_text)
                total_tokens += remaining_tokens
            # Дальше больше чанков не добавляем
            break

        context_parts.append(chunk_text)
        total_tokens += chunk_tokens

    context_text = "\n\n".join(context_parts)

    # Сводим в один user-промпт (messages ниже добавит system отдельно)
    prompt = f"""{few_shot}

Вопрос пользователя:
{query}

Контекст (найденные документы):
{context_text}

Ответь максимально точно и кратко (только финальный ответ).
"""
    return system_prompt, prompt



async def ask_llm(query: str, search_results: list, retries: int = 3, delay: float = 2.0) -> str:
    """Формирует промпт и отправляет в LLM"""
    system_prompt, user_prompt = build_prompt_with_context(query, search_results)

    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_completion_tokens=1000,
            )
            answer = resp.choices[0].message.content.strip() if resp.choices else ""

            if answer:
                return answer

            logger.warning(f"Пустой ответ от LLM (попытка {attempt}/{retries})")
            if attempt < retries:
                time.sleep(delay)

        except Exception as e:
            logger.exception(f"Ошибка вызова LLM (попытка {attempt}/{retries})")
            if attempt < retries:
                time.sleep(delay)

    # Если после всех попыток ответа нет
    return "Я не знаю. Позвоните по номеру 125"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text
    user_id = update.message.from_user.id if update.message.from_user else "unknown"
    logger.info(f"Вопрос от пользователя: {user_query}")

    # проверка на чувствительный запрос
    if is_sensitive_query(user_query):
        await update.message.reply_text(FALLBACK_SECRET_REPLY)
        logger.warning(f"Blocked sensitive query from user {user_id}: {user_query}")
        return
    
    # === 1. Эмбеддинг запроса ===
    query_vector = embedder.encode(user_query).tolist()

    # === 2. Поиск в Qdrant ===
    search_results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=10,
        with_payload=True
    )
    # фильтрация результатов на наличие секретного контента
    safe_results = []
    for r in search_results:
        text = (r.payload or {}).get("text", "")
        if contains_secret_like_text(text):
            logger.warning("Secret-like content detected in a chunk; redacting and skipping if necessary")
            redacted = redact_secrets(text)
            # if you want to exclude any chunk that had secrets entirely:
            # continue
            # otherwise attach redacted text:
            r.payload["text"] = redacted
        safe_results.append(r)

    if not safe_results:
        await update.message.reply_text(FALLBACK_SECRET_REPLY)
        return
    
    # Если лучший результат слишком "слабый", сразу возвращаем fallback-ответ
    if not safe_results or safe_results[0].score < 0.3:
        await update.message.reply_text(f"{FALLBACK_SECRET_REPLY}")
        logger.warning("Нет подходящих результатов в базе")
        return
    
    # === 3. Вызов LLM ===
    answer = await ask_llm(user_query, safe_results)

    if moderation_blocked(system_prompt + "\n" + user_prompt):
        await update.message.reply_text(FALLBACK_SECRET_REPLY)
        logger.warning("Prompt blocked by moderation")
        return

    await update.message.reply_text(answer)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот. Задай вопрос.")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
