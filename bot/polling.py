from bot.core import ReviewBot
from database import init_db
from config import Config, logger
from notifier import TaskNotifier
import time
import sys
import atexit


def run_polling():
    try:
        init_db()
        logger.info("Database initialized")

        bot = ReviewBot(Config.BOT_TOKEN)
        logger.info("Bot instance created")

        notifier = TaskNotifier(bot) if Config.NOTIFICATION_ENABLED else None

        def on_exit():
            if notifier:
                notifier.stop()
            logger.info("Application shutdown complete")

        atexit.register(on_exit)

        bot_info = bot.bot.self_get()
        if not bot_info.get('ok', False):
            raise ConnectionError("Failed to connect to bot API")

        logger.info(f"Bot connected: {bot_info.get('nick')}")
        bot.bot.start_polling()
        logger.info("Polling started")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}", exc_info=True)
        sys.exit(1)