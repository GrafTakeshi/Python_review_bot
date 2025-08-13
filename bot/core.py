from vkteams.bot import Bot
from vkteams.handler import CommandHandler, BotButtonCommandHandler, MessageHandler
from vkteams.types import InlineKeyboardMarkup, KeyboardButton
from keyboards import get_main_keyboard, get_confirmation_keyboard, get_yes_no_keyboard, get_task_keyboard
from config import Config, logger
from database import get_db_session
from models import Task
import re
import json
from contextlib import contextmanager


class ReviewBot:
    def __init__(self, token: str):
        self.bot = Bot(token=token, api_url_base=Config.API_URL)
        self.user_states = {}
        self.setup_handlers()
        logger.info("Bot initialized")

    def setup_handlers(self):
        @self.bot.command_handler(command="start")
        def handle_start(bot, event):
            if event.data['chat']['type'] != 'private':
                return
            self._handle_start(bot, event)

        @self.bot.button_handler()
        def handle_buttons(bot, event):
            if event.data['message']['chat']['type'] != 'private':
                return
            self._handle_button_click(bot, event)

        @self.bot.message_handler()
        def handle_messages(bot, event):
            if event.data['chat']['type'] != 'private':
                return
            self._process_user_message(bot, event)

    def _is_valid_url(self, url):
        return re.match(r'^https?://\S+$', url) is not None

    def _process_user_message(self, bot, event):
        try:
            user_id = event.message_author['userId']
            if user_id not in self.user_states:
                return

            state = self.user_states[user_id]
            text = event.text.strip()

            if state['step'] == 'youtrack_url':
                if not self._is_valid_url(text):
                    bot.send_text(
                        chat_id=state['chat_id'],
                        text="Некорректная ссылка. Введите правильный URL YouTrack:"
                    )
                    return
                state['data']['youtrack_url'] = text
                state['step'] = 'description'
                bot.send_text(
                    chat_id=state['chat_id'],
                    text="Введите описание задачи:"
                )

            elif state['step'] == 'description':
                if len(text) < 10:
                    bot.send_text(
                        chat_id=state['chat_id'],
                        text="Описание слишком короткое. Введите подробнее:"
                    )
                    return
                state['data']['description'] = text
                state['step'] = 'confluence_url'
                bot.send_text(
                    chat_id=state['chat_id'],
                    text="Введите ссылку на Confluence:"
                )

            elif state['step'] == 'confluence_url':
                if not self._is_valid_url(text):
                    bot.send_text(
                        chat_id=state['chat_id'],
                        text="Некорректная ссылка. Введите правильный URL Confluence:"
                    )
                    return
                state['data']['confluence_url'] = text
                state['step'] = 'confirmation'
                response = (
                    "Проверьте данные задачи:\n\n"
                    f"YouTrack: {state['data']['youtrack_url']}\n"
                    f"Описание: {state['data']['description']}\n"
                    f"Confluence: {state['data']['confluence_url']}"
                )
                bot.send_text(
                    chat_id=state['chat_id'],
                    text=response,
                    inline_keyboard_markup=get_confirmation_keyboard()
                )
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.from_chat,
                text="Произошла ошибка. Попробуйте снова."
            )
            if user_id in self.user_states:
                del self.user_states[user_id]

    def _handle_button_click(self, bot, event):
        try:
            callback_data = event.data.get('callbackData')

            if callback_data == "on_review":
                self._start_new_review_process(bot, event)
            elif callback_data == "my_tasks":
                self._show_my_tasks(bot, event)
            elif callback_data == "confirm_task":
                self._confirm_task(bot, event)
            elif callback_data == "cancel_task":
                self._cancel_task(bot, event)
            elif callback_data == "remove_review":
                self._start_remove_process(bot, event)
            elif callback_data == "do_review":
                self._start_review_process(bot, event)
            elif callback_data.startswith("review_task_"):
                self._show_task_for_review(bot, event)
            elif callback_data.startswith("approve_task_"):
                self._approve_task(bot, event)
            elif callback_data.startswith("request_revision_"):
                self._request_revision(bot, event)
            elif callback_data.startswith("confirm_approve_"):
                self._confirm_approve(bot, event)
            elif callback_data.startswith("confirm_revision_"):
                self._confirm_revision(bot, event)
            elif callback_data.startswith("select_task_"):
                self._show_task_for_removal(bot, event)
            elif callback_data.startswith("confirm_remove_"):
                self._confirm_removal(bot, event)
            elif callback_data == "cancel_remove":
                self._cancel_removal(bot, event)
            elif callback_data == "cancel_action":
                self._cancel_action(bot, event)
        except Exception as e:
            logger.error(f"Ошибка обработки кнопки: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Произошла ошибка при обработке команды"
            )

    def _show_task_for_review(self, bot, event):
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            chat_id = event.data['message']['chat']['chatId']
            user_id = event.data['from']['userId']

            with get_db_session() as db:
                task = db.query(Task).filter(Task.id == task_id).first()
                if not task:
                    raise ValueError("Задача не найдена")

                # Проверка, что пользователь не ревьюит свою задачу
                if task.user_id == user_id:
                    bot.send_text(
                        chat_id=chat_id,
                        text="Вы не можете ревьюить свои задачи!",
                        inline_keyboard_markup=get_main_keyboard()
                    )
                    return

                # Проверка, что задача еще не завершена
                if task.status:
                    bot.send_text(
                        chat_id=chat_id,
                        text="Эта задача уже завершена!",
                        inline_keyboard_markup=get_main_keyboard()
                    )
                    return

                response = (
                    "Задача на ревью:\n\n"
                    f"ID: {task.id}\n"
                    f"Создатель: {task.creator}\n"
                    f"YouTrack: {task.youtrack_url}\n"
                    f"Описание: {task.description}\n"
                    f"Confluence: {task.confluence_url}\n"
                    f"Одобрений: {task.approve_count}"
                )

                bot.send_text(
                    chat_id=chat_id,
                    text=response,
                    inline_keyboard_markup=get_task_keyboard(task.id)
                )

        except Exception as e:
            logger.error(f"Ошибка показа задачи: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при загрузке задачи"
            )

    def _handle_start(self, bot, event):
        try:
            user_name = self._get_user_name(event)
            bot.send_text(
                chat_id=event.data['chat']['chatId'] if event.type == 'callbackQuery' else event.from_chat,
                text=f"Привет, {user_name}! Выберите действие:",
                inline_keyboard_markup=get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка в обработчике start: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['chat']['chatId'] if event.type == 'callbackQuery' else event.from_chat,
                text="Произошла ошибка. Попробуйте позже."
            )

    def _start_new_review_process(self, bot, event):
        try:
            user_id = event.data['from']['userId']
            self.user_states[user_id] = {
                'step': 'youtrack_url',
                'data': {},
                'chat_id': event.data['message']['chat']['chatId']
            }
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Введите ссылку на задачу в YouTrack:"
            )
        except Exception as e:
            logger.error(f"Ошибка запуска процесса ревью: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при запуске процесса добавления задачи"
            )

    def _start_review_process(self, bot, event):
        try:
            reviewer_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            with get_db_session() as db:
                tasks = db.query(Task).filter(
                    Task.status == False,
                    Task.user_id != reviewer_id
                ).all()

                tasks_for_review = []
                for task in tasks:
                    approved_by = task.approved_by if task.approved_by else []
                    if reviewer_id not in approved_by:
                        tasks_for_review.append(task)

                if not tasks_for_review:
                    bot.send_text(
                        chat_id=chat_id,
                        text="Нет задач для ревью",
                        inline_keyboard_markup=get_main_keyboard()
                    )
                    return

                keyboard = InlineKeyboardMarkup(buttons_in_row=1)
                for task in tasks_for_review:
                    keyboard.row(
                        KeyboardButton(
                            text=f"Задача #{task.id}: {task.description[:50]}...",
                            callbackData=f"review_task_{task.id}"
                        )
                    )

                bot.send_text(
                    chat_id=chat_id,
                    text="Выберите задачу для ревью:",
                    inline_keyboard_markup=keyboard
                )

        except Exception as e:
            logger.error(f"Ошибка запуска ревью: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при получении списка задач для ревью"
            )

    def _approve_task(self, bot, event):
        task_id = int(event.data['callbackData'].split('_')[-1])
        chat_id = event.data['message']['chat']['chatId']

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            KeyboardButton(
                text="✅ Подтвердить одобрение",
                callbackData=f"confirm_approve_{task_id}"
            ),
            KeyboardButton(
                text="❌ Отмена",
                callbackData="cancel_action"
            )
        )

        bot.send_text(
            chat_id=chat_id,
            text="Вы уверены, что хотите одобрить эту задачу?",
            inline_keyboard_markup=keyboard
        )

    def _request_revision(self, bot, event):
        task_id = int(event.data['callbackData'].split('_')[-1])
        chat_id = event.data['message']['chat']['chatId']

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            KeyboardButton(
                text="✅ Подтвердить доработку",
                callbackData=f"confirm_revision_{task_id}"
            ),
            KeyboardButton(
                text="❌ Отмена",
                callbackData="cancel_action"
            )
        )

        bot.send_text(
            chat_id=chat_id,
            text="Вы уверены, что хотите запросить доработку?",
            inline_keyboard_markup=keyboard
        )

    def _confirm_approve(self, bot, event):
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            reviewer_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            with get_db_session() as db:
                task = db.query(Task).filter(Task.id == task_id).first()

                if not task:
                    raise ValueError("Задача не найдена")

                approved_by = task.approved_by if task.approved_by else []
                if reviewer_id not in approved_by:
                    approved_by.append(reviewer_id)
                    task.approved_by = approved_by
                    task.approve_count = len(approved_by)

                    if task.approve_count >= 2:
                        task.status = True
                        approvers = ", ".join(task.approved_by)
                        bot.send_text(
                            chat_id=Config.GROUP_CHAT_ID,
                            text=(
                                f"Задача {task.description}\n"
                                f"YouTrack: {task.youtrack_url}\n"
                                f"Confluence: {task.confluence_url}\n"
                                f"Успешно прошла ревью.\n"
                                f"Одобрили: {approvers}"
                            )
                        )

                    db.commit()

                    bot.send_text(
                        chat_id=chat_id,
                        text="Задача успешно одобрена!",
                        inline_keyboard_markup=get_main_keyboard()
                    )
                else:
                    bot.send_text(
                        chat_id=chat_id,
                        text="Вы уже одобряли эту задачу",
                        inline_keyboard_markup=get_main_keyboard()
                    )

        except Exception as e:
            logger.error(f"Approve error: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при одобрении задачи"
            )

    def _confirm_revision(self, bot, event):
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            reviewer_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            with get_db_session() as db:
                task = db.query(Task).filter(Task.id == task_id).first()

                if not task:
                    raise ValueError("Задача не найдена")

                bot.send_text(
                    chat_id=task.user_id,
                    text=(
                        f"Пользователь {reviewer_id} запросил доработку:\n"
                        f"Задача ID: {task.id}\n"
                        f"Описание: {task.description}"
                    )
                )

                bot.send_text(
                    chat_id=chat_id,
                    text="Запрос на доработку отправлен создателю задачи",
                    inline_keyboard_markup=get_main_keyboard()
                )

        except Exception as e:
            logger.error(f"Revision error: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при запросе доработки"
            )

    def _show_my_tasks(self, bot, event):
        try:
            with get_db_session() as db:
                user_id = event.data['from']['userId']
                tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.status == False
                ).all()

                if not tasks:
                    bot.send_text(
                        chat_id=event.data['message']['chat']['chatId'],
                        text="У вас нет задач на ревью"
                    )
                    return

                response = "Ваши задачи на ревью:\n\n"
                for task in tasks:
                    response += (
                        f"ID: {task.id}\n"
                        f"Описание: {task.description}\n"
                        f"YouTrack: {task.youtrack_url}\n"
                        f"Confluence: {task.confluence_url}\n\n"
                    )

                bot.send_text(
                    chat_id=event.data['message']['chat']['chatId'],
                    text=response
                )
        except Exception as e:
            logger.error(f"Ошибка показа задач: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при получении списка задач"
            )

    def _confirm_task(self, bot, event):
        try:
            user_id = event.data['from']['userId']
            if user_id not in self.user_states:
                raise ValueError("Данные задачи не найдены")

            task_data = self.user_states[user_id]['data']

            with get_db_session() as db:
                user_info = event.data['from']
                creator_name = f"{user_info.get('firstName', '')} {user_info.get('lastName', '')}".strip() or user_info[
                    'userId']

                new_task = Task(
                    user_id=user_id,
                    creator=creator_name,
                    description=task_data.get('description', ''),
                    youtrack_url=task_data.get('youtrack_url', ''),
                    confluence_url=task_data.get('confluence_url', ''),
                    status=False,
                    approve_count=0,
                    approved_by=[]
                )

                db.add(new_task)
                db.commit()

                group_message = (
                    f"Новая задача на ревью от {creator_name}:\n"
                    f"YouTrack: {new_task.youtrack_url}\n"
                    f"Описание: {new_task.description}\n"
                    f"Confluence: {new_task.confluence_url}"
                )

                try:
                    response = bot.send_text(
                        chat_id=Config.GROUP_CHAT_ID,
                        text=group_message
                    )

                    if not response.json().get('ok', False):
                        logger.error(f"Ошибка отправки в группу: {response.text}")
                        bot.send_text(
                            chat_id=self.user_states[user_id]['chat_id'],
                            text="Не удалось отправить уведомление в группу. Проверьте права бота."
                        )
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления в группу: {str(e)}", exc_info=True)

                bot.send_text(
                    chat_id=self.user_states[user_id]['chat_id'],
                    text="Задача успешно добавлена на ревью!",
                    inline_keyboard_markup=get_main_keyboard()
                )
                del self.user_states[user_id]

        except Exception as e:
            logger.error(f"Ошибка подтверждения задачи: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=self.user_states[user_id]['chat_id'],
                text="Ошибка при сохранении задачи"
            )

    def _cancel_task(self, bot, event):
        try:
            user_id = event.data['from']['userId']
            if user_id in self.user_states:
                del self.user_states[user_id]
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Добавление задачи отменено",
                inline_keyboard_markup=get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка отмены задачи: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при отмене задачи"
            )

    def _start_remove_process(self, bot, event):
        try:
            user_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            with get_db_session() as db:
                tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.status == False
                ).all()

                if not tasks:
                    bot.send_text(
                        chat_id=chat_id,
                        text="У вас нет задач на ревью"
                    )
                    return

                keyboard = InlineKeyboardMarkup()
                for task in tasks:
                    description = task.description[:50] + '...' if len(task.description) > 50 else task.description
                    keyboard.row(
                        KeyboardButton(
                            text=description,
                            callbackData=f"select_task_{task.id}"
                        )
                    )

                bot.send_text(
                    chat_id=chat_id,
                    text="Какую задачу вы хотите снять?",
                    inline_keyboard_markup=keyboard
                )

        except Exception as e:
            logger.error(f"Ошибка запуска процесса снятия: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при запуске процесса снятия задачи"
            )

    def _show_task_for_removal(self, bot, event):
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            chat_id = event.data['message']['chat']['chatId']

            with get_db_session() as db:
                task = db.query(Task).filter(Task.id == task_id).first()

                if not task:
                    raise ValueError("Задача не найдена")

                response = (
                    "Вы точно хотите снять эту задачу с ревью?\n\n"
                    f"ID: {task.id}\n"
                    f"Создатель: {task.creator}\n"
                    f"YouTrack: {task.youtrack_url}\n"
                    f"Описание: {task.description}\n"
                    f"Confluence: {task.confluence_url}\n"
                    f"Одобрили: {task.approve_count}"
                )

                bot.send_text(
                    chat_id=chat_id,
                    text=response,
                    inline_keyboard_markup=get_yes_no_keyboard(task.id)
                )

        except Exception as e:
            logger.error(f"Ошибка показа задачи: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при отображении задачи"
            )

    def _confirm_removal(self, bot, event):
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            chat_id = event.data['message']['chat']['chatId']

            with get_db_session() as db:
                task = db.query(Task).filter(Task.id == task_id).first()

                if task:
                    db.delete(task)
                    db.commit()
                    bot.send_text(
                        chat_id=chat_id,
                        text="Задача успешно снята с ревью!",
                        inline_keyboard_markup=get_main_keyboard()
                    )
                else:
                    raise ValueError("Задача не найдена")

        except Exception as e:
            logger.error(f"Ошибка подтверждения удаления: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при удалении задачи"
            )

    def _cancel_removal(self, bot, event):
        try:
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Отмена снятия задачи",
                inline_keyboard_markup=get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка отмены удаления: {str(e)}", exc_info=True)
            bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при отмене операции"
            )

    def _cancel_action(self, bot, event):
        bot.send_text(
            chat_id=event.data['message']['chat']['chatId'],
            text="Действие отменено",
            inline_keyboard_markup=get_main_keyboard()
        )

    def _get_user_name(self, event):
        """Безопасное получение имени пользователя"""
        try:
            if event.type == 'callbackQuery':
                user_data = event.data['from']
            else:
                user_data = event.message_author

            if isinstance(user_data, dict):
                first_name = user_data.get('firstName', '')
                last_name = user_data.get('lastName', '')
                return f"{first_name} {last_name}".strip() or user_data.get('userId', 'Unknown')
            return str(user_data) if user_data else 'Unknown'
        except Exception as e:
            logger.error(f"Ошибка получения имени пользователя: {str(e)}", exc_info=True)
            return 'Unknown'