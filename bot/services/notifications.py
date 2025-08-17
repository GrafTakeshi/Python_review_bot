from vkteams.constant import ParseMode
from config import Config
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot):
        self.bot = bot

    def send_daily_notification(self):
        try:
            tasks = self.bot.task_service.get_pending_tasks()

            if not tasks:
                logger.info("No tasks for notification")
                return

            message = "📅 *Доброе утро, сегодня у нас следующие задачи:*\n\n"
            for task in tasks:
                message += (
                    f"• *Создатель:* {task.creator}\n"
                    f"• *Описание:* {task.description}\n"
                    f"• [YouTrack]({task.youtrack_url})\n"
                    f"• [Confluence]({task.confluence_url})\n\n"
                )

            self.bot.bot.send_text(
                chat_id=Config.GROUP_CHAT_ID,
                text=message,
                parse_mode=ParseMode.MARKDOWNV2.value
            )
        except Exception as e:
            logger.error(f"Notification error: {str(e)}")