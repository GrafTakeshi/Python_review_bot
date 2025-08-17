from polling import run_polling
from config import logger

if __name__ == "__main__":
    logger.info("Starting bot...")
    try:
        run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
        exit(1)