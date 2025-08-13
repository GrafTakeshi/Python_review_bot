from bot.polling import run_polling
from config import logger

if __name__ == "__main__":
    logger.info("Starting bot...")
    try:
        run_polling()
    except Exception as e:
        logger.error(f"Critical error: {e}")