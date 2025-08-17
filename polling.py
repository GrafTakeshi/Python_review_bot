from bot.core import ReviewBot
from database.manager import DatabaseManager
from config import Config, logger
from notifier import TaskNotifier
import time  # Добавьте этот импорт
import atexit
import sys

def run_polling():
    try:
        # Инициализация БД
        db_manager = DatabaseManager()
        db_manager.init_db()
        logger.info("Database initialized")

        # Создание бота
        bot = ReviewBot()
        logger.info("Bot instance created")

        # Запуск уведомлений
        notifier = TaskNotifier(bot) if Config.NOTIFICATION_ENABLED else None

        # Обработка завершения
        def on_exit():
            if notifier:
                notifier.stop()
            logger.info("Application shutdown complete")

        atexit.register(on_exit)

        # Проверка подключения
        bot_info = bot.bot.self_get()
        if not bot_info.get('ok', False):
            raise ConnectionError("Failed to connect to bot API")

        logger.info(f"Bot connected: {bot_info.get('nick')}")
        bot.bot.start_polling()
        logger.info("Polling started")

        # Основной цикл
        while True:
            time.sleep(1)  # Теперь time доступен

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}", exc_info=True)
        sys.exit(1)