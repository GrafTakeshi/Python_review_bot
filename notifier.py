import threading
import schedule
import time
import pytz
from datetime import datetime
from config import Config, logger
from bot.core import ReviewBot

class TaskNotifier:
    def __init__(self, bot: ReviewBot):
        if not Config.NOTIFICATION_ENABLED:
            logger.info("Notifications disabled")
            return

        self.bot = bot
        self._running = True
        self._setup_scheduler()

    def _setup_scheduler(self):
        def run_continuously():
            schedule.every().day.at(
                Config.NOTIFICATION_TIME,
                Config.NOTIFICATION_TZ
            ).do(self._send_daily_notifications)

            while self._running:
                schedule.run_pending()
                time.sleep(60)

        self.thread = threading.Thread(
            target=run_continuously,
            daemon=True
        )
        self.thread.start()

    def _send_daily_notifications(self):
        self.bot.notification_service.send_daily_notification()

    def stop(self):
        self._running = False
        schedule.clear()