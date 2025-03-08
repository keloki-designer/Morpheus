# config.py
"""
Модуль с конфигурационными параметрами проекта
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Общие настройки
LOG_LEVEL = "INFO"
DATABASE_PATH = "database.sqlite"
SESSIONS_PATH = "sessions/"
CHAT_HISTORY_PATH = "chat_history/"

# Настройки Telegram
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER")
SESSION_NAME = "user_session"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Токен для бота-контроллера

# Настройки для генерации ответов
# Может быть "openai" или "gigachat"
API_PROVIDER = os.getenv("API_PROVIDER", "gigachat")

# Настройки OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4"

# Настройки Sber GigaChat
CERT_PATH = "russian_trusted_root_ca.cer"
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
GIGACHAT_MODEL = "GigaChat"

# Настройки Google Calendar
GOOGLE_CREDENTIALS_FILE = "effortless-leaf-453113-t9-4ff924642d2f.json"
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

# Настройки для работы имитатора
# Промпт, который будет использоваться для генерации ответов
IMITATOR_PROMPT = """
Ты - помощник для проведения предварительных консультаций и назначения встреч. 
Твоя задача - вежливо ответить на вопросы пользователя, собрать базовую информацию 
о его потребностях и предложить видеовстречу через Google Meet.

Придерживайся следующих правил:
1. Общайся в дружелюбном, но профессиональном тоне
2. Не пиши слишком длинные сообщения (максимум 3-4 предложения)
3. Если пользователь интересуется услугами или задает вопросы, отвечай кратко и информативно
4. Предлагай видеоконсультацию после 2-3 обмена сообщениями
5. Если пользователь согласен на встречу, запроси удобное для него время
6. После получения информации о времени, подтверди создание встречи в Google Calendar
7. Если пользователь не готов к встрече, продолжай диалог и отвечай на вопросы

История предыдущего общения:
{chat_history}

Текущее сообщение пользователя:
{user_message}

Твой ответ:
"""

# Максимальная длина истории диалога (в символах)
MAX_HISTORY_LENGTH = 2000