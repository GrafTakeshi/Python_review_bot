import logging
import sys
import io

# Фикс кодировки для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class Config:
    BOT_TOKEN = "Токен"
    API_URL = "адрес апи"
    DB_URL = "sqlite:///tasks.db"
    LOGGING = True
    LOG_LEVEL = logging.DEBUG
    GROUP_CHAT_ID = "группа@chat.agent"
    NOTIFICATION_TIME = "09:00"
    NOTIFICATION_TZ = "Europe/Moscow"
    NOTIFICATION_ENABLED = True

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)