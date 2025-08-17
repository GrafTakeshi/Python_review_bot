from .base import BaseHandler
import logging

logger = logging.getLogger(__name__)


class CommandHandler(BaseHandler):
    def handle_start(self, event):
        try:
            if event.data['chat']['type'] != 'private':
                return

            user_name = self._get_user_name(event)
            self.bot.bot.send_text(
                chat_id=event.from_chat,
                text=f"Привет, {user_name}! Выберите действие:",
                inline_keyboard_markup=self.keyboards.get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Error in start handler: {str(e)}")
            self.bot.bot.send_text(
                chat_id=event.from_chat,
                text="Произошла ошибка. Попробуйте позже."
            )