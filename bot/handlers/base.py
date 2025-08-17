import logging
from bot.keyboards.builder import KeyboardBuilder

logger = logging.getLogger(__name__)


class BaseHandler:
    def __init__(self, bot):
        self.bot = bot
        self.state = bot.state_manager
        self.tasks = bot.task_service
        self.notifier = bot.notification_service
        self.keyboards = KeyboardBuilder()

    def _get_user_name(self, event):
        try:
            user_data = event.data['from'] if event.type == 'callbackQuery' else event.message_author
            first_name = user_data.get('firstName', '')
            last_name = user_data.get('lastName', '')
            return f"{first_name} {last_name}".strip() or user_data.get('userId', 'Unknown')
        except Exception as e:
            logger.error(f"Error getting user name: {str(e)}")
            return 'Unknown'