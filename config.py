import logging
import os

# Bot token
AIOGRAM_TOKEN = "7714813862:AAGLtT2oS6Q6RGJH4_uE-lf5nNkGPCJYGr8"

# File for storing auth data
AUTH_DATA_FILE = "auth_data.json"

# Telethon session filename
TELETHON_SESSION_FILENAME = 'telethon_session'

# Restart parameters
MAX_RESTART_ATTEMPTS = 5
RESTART_DELAY = 10

# Auto-auth flag
AUTO_AUTH_ON_START = True

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_logs.log",encoding="UTf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
