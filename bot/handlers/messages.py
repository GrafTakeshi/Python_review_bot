from .base import BaseHandler
from vkteams.types import InlineKeyboardMarkup, KeyboardButton
import re
import logging

logger = logging.getLogger(__name__)


class MessageHandler(BaseHandler):
    def handle(self, event):
        try:
            if event.data['chat']['type'] != 'private':
                return

            user_id = event.message_author['userId']
            state = self.state.get_state(user_id)

            if not state:
                return

            text = event.text.strip()

            if state['step'] == 'youtrack_url':
                self._handle_youtrack_url(event, user_id, text)
            elif state['step'] == 'description':
                self._handle_description(event, user_id, text)
            elif state['step'] == 'confluence_url':
                self._handle_confluence_url(event, user_id, text)

        except Exception as e:
            logger.error(f"Message handling error: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.from_chat,
                text="Произошла ошибка. Попробуйте снова."
            )

    def _handle_youtrack_url(self, event, user_id, text):
        if not self._is_valid_url(text):
            self.bot.bot.send_text(
                chat_id=event.from_chat,
                text="Некорректная ссылка. Введите правильный URL YouTrack:"
            )
            return

        self.state.update_state(
            user_id=user_id,
            step='description',
            data={'youtrack_url': text}
        )

        self.bot.bot.send_text(
            chat_id=event.from_chat,
            text="Введите описание задачи:"
        )

    def _handle_description(self, event, user_id, text):
        if len(text) < 10:
            self.bot.bot.send_text(
                chat_id=event.from_chat,
                text="Описание слишком короткое. Введите подробнее:"
            )
            return

        self.state.update_state(
            user_id=user_id,
            step='confluence_url',
            data={'description': text}
        )

        self.bot.bot.send_text(
            chat_id=event.from_chat,
            text="Введите ссылку на Confluence:"
        )

    def _handle_confluence_url(self, event, user_id, text):
        if not self._is_valid_url(text):
            self.bot.bot.send_text(
                chat_id=event.from_chat,
                text="Некорректная ссылка. Введите правильный URL Confluence:"
            )
            return

        state = self.state.get_state(user_id)
        state['data']['confluence_url'] = text

        response = (
            "Проверьте данные задачи:\n\n"
            f"YouTrack: {state['data']['youtrack_url']}\n"
            f"Описание: {state['data']['description']}\n"
            f"Confluence: {state['data']['confluence_url']}"
        )

        self.bot.bot.send_text(
            chat_id=event.from_chat,
            text=response,
            inline_keyboard_markup=self.keyboards.get_confirmation_keyboard()
        )

    def _is_valid_url(self, url):
        return re.match(r'^https?://\S+$', url) is not None