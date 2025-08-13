import threading
import schedule
import time
import pytz
from datetime import datetime
from database import get_db_session
from models import Task
from config import Config, logger
from bot.core import ReviewBot


class TaskNotifier:
    def __init__(self, bot: ReviewBot):
        if not Config.NOTIFICATION_ENABLED:
            logger.info("Daily notifications are disabled in config")
            return

        self.bot = bot
        self._running = True
        self._setup_scheduler()

    def _setup_scheduler(self):
        def run_continuously():
            logger.info(f"Starting scheduler for {Config.NOTIFICATION_TIME} {Config.NOTIFICATION_TZ}")
            schedule.every().day.at(Config.NOTIFICATION_TIME).do(
                self._send_daily_notifications
            )

            while self._running:
                try:
                    schedule.run_pending()
                    time.sleep(60)
                except Exception as e:
                    logger.error(f"Scheduler error: {str(e)}", exc_info=True)

        self.thread = threading.Thread(target=run_continuously, daemon=True)
        self.thread.start()

    def stop(self):
        self._running = False
        schedule.clear()
        logger.info("Scheduler stopped")

    def _send_daily_notifications(self):
        try:
            logger.info("Preparing daily notifications...")
            with get_db_session() as db:
                tasks = db.query(Task).filter(Task.status == False).all()

                if not tasks:
                    logger.info("No active tasks found for notification")
                    return

                message = "📅 *Ежедневное уведомление о задачах на ревью:*\n\n"
                for task in tasks:
                    message += (
                        f"• *Создатель:* {task.creator}\n"
                        f"• *Описание:* {task.description}\n"
                        f"• [YouTrack]({task.youtrack_url})\n"
                        f"• [Confluence]({task.confluence_url})\n"
                        f"• Одобрений: {task.approve_count}\n\n"
                    )

                self.bot.bot.send_text(
                    chat_id=Config.GROUP_CHAT_ID,
                    text=message,
                    parse_mode="Markdown"
                )
                logger.info("Daily notification sent successfully")

        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}", exc_info=True)