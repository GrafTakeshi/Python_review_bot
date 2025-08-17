from vkteams.bot import Bot as VkTeamsBot
from bot.handlers.commands import CommandHandler
from bot.handlers.messages import MessageHandler
from bot.handlers.callbacks import CallbackHandler
from bot.services.tasks import TaskService
from bot.services.notifications import NotificationService
from bot.states.user import UserStateManager
from config import Config
import logging

logger = logging.getLogger(__name__)


class ReviewBot:
    def __init__(self, token: str = Config.BOT_TOKEN):
        self.bot = VkTeamsBot(
            token=token,
            api_url_base=Config.API_URL
        )
        self.state_manager = UserStateManager()
        self.task_service = TaskService()
        self.notification_service = NotificationService(self)

        self._setup_handlers()
        logger.info("Bot initialized")

    def _setup_handlers(self):
        command_handler = CommandHandler(self)
        message_handler = MessageHandler(self)
        callback_handler = CallbackHandler(self)

        @self.bot.command_handler(command="start")
        def handle_start(bot, event):
            command_handler.handle_start(event)

        @self.bot.message_handler()
        def handle_message(bot, event):
            message_handler.handle(event)

        @self.bot.button_handler()
        def handle_button(bot, event):
            callback_handler.handle(event)