from .base import BaseHandler
from vkteams.types import InlineKeyboardMarkup, KeyboardButton
from database.manager import DatabaseManager
from config import Config
import logging
import json
from datetime import datetime

from ..models.task import Task

logger = logging.getLogger(__name__)


class CallbackHandler(BaseHandler):
    """
    Обработчик callback-событий от inline-кнопок
    Реализует всю бизнес-логику взаимодействия с кнопками
    """

    def handle(self, event):
        """
        Главный обработчик callback-событий от inline-кнопок
        Обрабатывает все типы нажатий на кнопки и делегирует выполнение соответствующим методам

        Args:
            event: Объект события от VK Teams Bot API
        """
        try:
            if not event.data or 'callbackData' not in event.data:
                logger.warning("Получен callback без данных")
                return

            callback_data = event.data['callbackData']
            logger.debug(f"Обработка callback: {callback_data}")

            # Основной роутер callback-событий
            if callback_data == "on_review":
                self._start_new_review_process(event)
            elif callback_data == "my_tasks":
                self._show_my_tasks(event)
            elif callback_data == "confirm_task":
                self._confirm_task(event)
            elif callback_data == "cancel_task":
                self._cancel_task(event)
            elif callback_data == "remove_review":
                self._start_remove_process(event)
            elif callback_data == "do_review":
                self._start_review_process(event)
            elif callback_data.startswith("review_task_"):
                self._show_task_for_review(event)
            elif callback_data.startswith("approve_task_"):
                self._approve_task(event)
            elif callback_data.startswith("request_revision_"):
                self._request_revision(event)
            elif callback_data.startswith("confirm_approve_"):
                self._confirm_approve(event)
            elif callback_data.startswith("confirm_revision_"):
                self._confirm_revision(event)
            elif callback_data.startswith("select_task_"):
                self._show_task_for_removal(event)
            elif callback_data.startswith("confirm_remove_"):
                self._confirm_removal(event)
            elif callback_data == "cancel_remove":
                self._cancel_removal(event)
            elif callback_data == "cancel_action":
                self._cancel_action(event)
            else:
                logger.warning(f"Неизвестный callback: {callback_data}")
                self._handle_unknown_callback(event)

        except Exception as e:
            logger.error(f"Ошибка обработки callback: {str(e)}", exc_info=True)
            self._send_error_message(event)

    def _handle_unknown_callback(self, event):
        """Обработка неизвестных callback-событий"""
        self.bot.bot.send_text(
            chat_id=event.data['message']['chat']['chatId'],
            text="⚠️ Неизвестная команда",
            inline_keyboard_markup=self.keyboards.get_main_keyboard()
        )

    def _send_error_message(self, event):
        """Отправка сообщения об ошибке"""
        self.bot.bot.send_text(
            chat_id=event.data['message']['chat']['chatId'],
            text="❌ Произошла ошибка при обработке запроса",
            inline_keyboard_markup=self.keyboards.get_main_keyboard()
        )

    def _start_new_review_process(self, event):
        """
        Начинает процесс добавления новой задачи на ревью
        Устанавливает начальное состояние пользователя

        Args:
            event (Event): Объект события callback
        """
        try:
            user_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            logger.info(f"Starting new review process for user {user_id}")

            self.state.set_state(
                user_id=user_id,
                step='youtrack_url',
                data={
                    'chat_id': chat_id,
                    'start_time': datetime.now().isoformat()
                }
            )

            self.bot.bot.send_text(
                chat_id=chat_id,
                text="Введите ссылку на задачу в YouTrack:"
            )

        except Exception as e:
            logger.error(f"Error starting review process: {str(e)}", exc_info=True)
            raise

    def _confirm_task(self, event):
        """Подтверждает и сохраняет новую задачу"""
        try:
            user_id = event.data['from']['userId']
            state = self.state.get_state(user_id)

            if not state or 'data' not in state:
                raise ValueError("Не найдены данные задачи")

            # Получаем информацию о пользователе
            user_info = event.data['from']
            creator_name = f"{user_info.get('firstName', '')} {user_info.get('lastName', '')}".strip()
            creator_name = creator_name if creator_name else user_info.get('userId', 'Unknown')

            # Формируем данные задачи
            task_data = {
                'user_id': user_id,
                'creator': creator_name,
                'description': state['data'].get('description', ''),
                'youtrack_url': state['data'].get('youtrack_url', ''),
                'confluence_url': state['data'].get('confluence_url', ''),
                'status': False,
                'approve_count': 0,
                'approved_by': []
            }

            with DatabaseManager().session() as db:
                # Создаем и сохраняем задачу
                task = self.tasks.create_task(db, task_data)
                db.commit()

                # Отправляем уведомления
                self._notify_task_creation(task, event.data['message']['chat']['chatId'])

                # Отправляем подтверждение
                self.bot.bot.send_text(
                    chat_id=state['data']['chat_id'],
                    text=f"✅ Задача #{task.id} успешно создана!",
                    inline_keyboard_markup=self.keyboards.get_main_keyboard()
                )

                # Очищаем состояние
                self.state.clear_state(user_id)

        except ValueError as e:
            logger.error(f"Ошибка валидации: {str(e)}")
            self._send_error(event, "Ошибка: неполные данные задачи")
        except Exception as e:
            logger.error(f"Ошибка создания задачи: {str(e)}", exc_info=True)
            self._send_error(event, "Ошибка при сохранении задачи")

    def _notify_task_creation(self, task, chat_id):
        """Отправляет уведомления о новой задаче"""
        try:
            # Уведомление в групповой чат
            group_message = (
                "🚀 Новая задача на ревью!\n\n"
                f"Автор: {task.creator}\n"
                f"Описание: {task.description}\n"
                f"YouTrack: {task.youtrack_url}\n"
                f"Confluence: {task.confluence_url}"
            )

            self.bot.bot.send_text(
                chat_id=Config.GROUP_CHAT_ID,
                text=group_message
            )

            # Уведомление создателю
            self.bot.bot.send_text(
                chat_id=chat_id,
                text=f"Ваша задача отправлена на ревью (ID: {task.id})"
            )

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {str(e)}")

    def _send_error(self, event, message):
        """Отправляет сообщение об ошибке"""
        self.bot.bot.send_text(
            chat_id=event.data['message']['chat']['chatId'],
            text=f"❌ {message}",
            inline_keyboard_markup=self.keyboards.get_main_keyboard()
        )

    def _format_user_name(self, user_info):
        """Форматирует имя пользователя из данных события"""
        first_name = user_info.get('firstName', '').strip()
        last_name = user_info.get('lastName', '').strip()

        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        elif last_name:
            return last_name
        return user_info.get('userId', 'Unknown')

    def _show_task_for_review(self, event):
        """
        Отображает полную информацию о задаче для ревью

        Args:
            event (Event): Объект события callback
        """
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            chat_id = event.data['message']['chat']['chatId']
            user_id = event.data['from']['userId']

            logger.info(f"Showing task {task_id} for review by user {user_id}")

            with DatabaseManager().session() as db:
                task = self.tasks.get_task(db, task_id)

                if not task:
                    raise ValueError(f"Task {task_id} not found")

                # Проверка, что пользователь не ревьюит свою задачу
                if task.user_id == user_id:
                    self.bot.bot.send_text(
                        chat_id=chat_id,
                        text="⚠️ Вы не можете ревьюить свои задачи!",
                        inline_keyboard_markup=self.keyboards.get_main_keyboard()
                    )
                    return

                # Проверка статуса задачи
                if task.status:
                    self.bot.bot.send_text(
                        chat_id=chat_id,
                        text="✅ Эта задача уже завершена!",
                        inline_keyboard_markup=self.keyboards.get_main_keyboard()
                    )
                    return

                # Формирование сообщения с информацией о задаче
                approved_by = ", ".join(task.approved_by) if task.approved_by else "пока нет"

                response = (
                    "📝 Задача на ревью\n\n"
                    f"ID: #{task.id}\n"
                    f"Автор: {task.creator}\n"
                    f"Дата создания: {task.created_at.strftime('%d.%m.%Y')}\n\n"
                    f"Описание:\n{task.description}\n\n"
                    f"Ссылки:\n"
                    f"YouTrack: {task.youtrack_url}\n"
                    f"Confluence: {task.confluence_url}\n\n"
                    f"Одобрений: {task.approve_count}\n"
                    f"Одобрили: {approved_by}"
                )

                # Отправка сообщения с кнопками действий
                self.bot.bot.send_text(
                    chat_id=chat_id,
                    text=response,
                    inline_keyboard_markup=self.keyboards.get_task_keyboard(task.id)
                )

        except Exception as e:
            logger.error(f"Error showing task: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="❌ Ошибка при загрузке задачи"
            )

    def _approve_task(self, event):
        """
        Инициирует процесс одобрения задачи
        Запрашивает подтверждение перед одобрением

        Args:
            event (Event): Объект события callback
        """
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            chat_id = event.data['message']['chat']['chatId']

            logger.info(f"Approval requested for task {task_id}")

            # Создаем клавиатуру для подтверждения
            keyboard = InlineKeyboardMarkup()
            keyboard.row(
                KeyboardButton(
                    text="✅ Подтвердить одобрение",
                    callbackData=f"confirm_approve_{task_id}",
                    style="primary"
                ),
                KeyboardButton(
                    text="❌ Отмена",
                    callbackData="cancel_action",
                    style="attention"
                )
            )

            self.bot.bot.send_text(
                chat_id=chat_id,
                text="Вы уверены, что хотите одобрить эту задачу?",
                inline_keyboard_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Error initiating approval: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="❌ Ошибка при обработке запроса"
            )

    def _confirm_approve(self, event):
        """
        Подтверждает одобрение задачи и обновляет данные в БД

        Args:
            event (Event): Объект события callback
        """
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            user_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            logger.info(f"Confirming approval for task {task_id} by user {user_id}")

            with DatabaseManager().session() as db:
                task = self.tasks.get_task(db, task_id)

                if not task:
                    raise ValueError(f"Task {task_id} not found")

                # Проверяем, не одобрял ли уже пользователь
                if user_id in task.approved_by:
                    self.bot.bot.send_text(
                        chat_id=chat_id,
                        text="ℹ️ Вы уже одобряли эту задачу",
                        inline_keyboard_markup=self.keyboards.get_main_keyboard()
                    )
                    return

                # Обновляем список одобривших
                approved_by = task.approved_by or []
                approved_by.append(user_id)
                task.approved_by = approved_by
                task.approve_count = len(approved_by)

                # Проверяем, достигнуто ли необходимое количество одобрений
                if task.approve_count >= 2:  # Пример: требуется 2 одобрения
                    task.status = True
                    task.completed_at = datetime.now()

                    # Отправляем уведомление в группу
                    approvers = ", ".join(task.approved_by)
                    group_message = (
                        "🎉 Задача завершена!\n\n"
                        f"ID: #{task.id}\n"
                        f"Описание: {task.description}\n\n"
                        f"Одобрили: {approvers}"
                    )

                    self.bot.bot.send_text(
                        chat_id=Config.GROUP_CHAT_ID,
                        text=group_message
                    )

                db.commit()

                # Отправляем подтверждение пользователю
                self.bot.bot.send_text(
                    chat_id=chat_id,
                    text="✅ Вы успешно одобрили задачу!",
                    inline_keyboard_markup=self.keyboards.get_main_keyboard()
                )

        except Exception as e:
            logger.error(f"Error confirming approval: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="❌ Ошибка при одобрении задачи"
            )

    # Остальные методы (_request_revision, _start_review_process и т.д.)
    # реализуются по аналогии с приведенными выше примерами
    # с сохранением одинакового стиля и подхода

    def _cancel_task(self, event):
        """Отменяет процесс создания задачи"""
        user_id = event.data['from']['userId']
        self.state.clear_state(user_id)
        self.bot.bot.send_text(
            chat_id=event.data['message']['chat']['chatId'],
            text="❌ Добавление задачи отменено",
            inline_keyboard_markup=self.keyboards.get_main_keyboard()
        )

    def _cancel_action(self, event):
        """Отменяет текущее действие"""
        self.bot.bot.send_text(
            chat_id=event.data['message']['chat']['chatId'],
            text="❌ Действие отменено",
            inline_keyboard_markup=self.keyboards.get_main_keyboard()
        )

    def _show_my_tasks(self, event):
        try:
            user_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            with DatabaseManager().session() as db:
                tasks = self.tasks.get_user_tasks(db, user_id)

                if not tasks:
                    self.bot.bot.send_text(
                        chat_id=chat_id,
                        text="У вас нет активных задач на ревью",
                        inline_keyboard_markup=self.keyboards.get_main_keyboard()
                    )
                    return

                message = "Ваши задачи на ревью:\n\n"
                for task in tasks:
                    message += (
                        f"ID: {task.id}\n"
                        f"Описание: {task.description}\n"
                        f"Статус: {'Завершена' if task.status else 'На ревью'}\n"
                        f"Одобрений: {task.approve_count}\n\n"
                    )

                self.bot.bot.send_text(
                    chat_id=chat_id,
                    text=message,
                    inline_keyboard_markup=self.keyboards.get_main_keyboard()
                )

        except Exception as e:
            logger.error(f"Error showing tasks: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при получении списка задач"
            )

    def _start_review_process(self, event):
        try:
            user_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            with DatabaseManager().session() as db:
                tasks = self.tasks.get_reviewable_tasks(db, user_id)

                if not tasks:
                    self.bot.bot.send_text(
                        chat_id=chat_id,
                        text="Нет доступных задач для ревью",
                        inline_keyboard_markup=self.keyboards.get_main_keyboard()
                    )
                    return

                keyboard = InlineKeyboardMarkup(buttons_in_row=1)
                for task in tasks:
                    keyboard.row(
                        KeyboardButton(
                            text=f"Задача #{task.id}: {task.description[:30]}...",
                            callbackData=f"review_task_{task.id}"
                        )
                    )

                self.bot.bot.send_text(
                    chat_id=chat_id,
                    text="Выберите задачу для ревью:",
                    inline_keyboard_markup=keyboard
                )

        except Exception as e:
            logger.error(f"Error starting review: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при получении списка задач"
            )

    def _start_remove_process(self, event):
        """Начинает процесс снятия задачи с ревью"""
        try:
            user_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            with DatabaseManager().session() as db:
                tasks = self.tasks.get_user_tasks(db, user_id)

                if not tasks:
                    self.bot.bot.send_text(
                        chat_id=chat_id,
                        text="У вас нет задач для снятия с ревью",
                        inline_keyboard_markup=self.keyboards.get_main_keyboard()
                    )
                    return

                keyboard = InlineKeyboardMarkup(buttons_in_row=1)
                for task in tasks:
                    keyboard.row(
                        KeyboardButton(
                            text=f"Задача #{task.id}: {task.description[:30]}...",
                            callbackData=f"select_task_{task.id}"
                        )
                    )

                self.bot.bot.send_text(
                    chat_id=chat_id,
                    text="Выберите задачу для снятия с ревью:",
                    inline_keyboard_markup=keyboard
                )

        except Exception as e:
            logger.error(f"Error starting remove process: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при получении списка задач"
            )

    def _start_remove_process(self, event):
        """Начинает процесс снятия задачи с ревью"""
        try:
            user_id = event.data['from']['userId']
            chat_id = event.data['message']['chat']['chatId']

            with DatabaseManager().session() as db:
                tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.status == False
                ).all()

                if not tasks:
                    self.bot.bot.send_text(
                        chat_id=chat_id,
                        text="У вас нет активных задач для снятия",
                        inline_keyboard_markup=self.keyboards.get_main_keyboard()
                    )
                    return

                keyboard = InlineKeyboardMarkup(buttons_in_row=1)
                for task in tasks:
                    keyboard.row(
                        KeyboardButton(
                            text=f"Задача #{task.id}: {task.description[:30]}...",
                            callbackData=f"select_task_{task.id}"
                        )
                    )

                self.bot.bot.send_text(
                    chat_id=chat_id,
                    text="Выберите задачу для снятия с ревью:",
                    inline_keyboard_markup=keyboard
                )

        except Exception as e:
            logger.error(f"Error starting remove process: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при получении списка задач"
            )

    def _show_task_for_removal(self, event):
        """Показывает задачу для подтверждения снятия"""
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            chat_id = event.data['message']['chat']['chatId']
            user_id = event.data['from']['userId']

            with DatabaseManager().session() as db:
                task = db.query(Task).filter(
                    Task.id == task_id,
                    Task.user_id == user_id
                ).first()

                if not task:
                    raise ValueError("Задача не найдена или не принадлежит вам")

                response = (
                    "Вы точно хотите снять эту задачу с ревью?\n\n"
                    f"ID: {task.id}\n"
                    f"Описание: {task.description}\n"
                    f"Статус: {'Завершена' if task.status else 'На ревью'}\n"
                    f"Одобрений: {task.approve_count}"
                )

                keyboard = InlineKeyboardMarkup()
                keyboard.row(
                    KeyboardButton(
                        text="✅ Да, снять",
                        callbackData=f"confirm_remove_{task.id}",
                        style="primary"
                    ),
                    KeyboardButton(
                        text="❌ Нет, отменить",
                        callbackData="cancel_remove",
                        style="attention"
                    )
                )

                self.bot.bot.send_text(
                    chat_id=chat_id,
                    text=response,
                    inline_keyboard_markup=keyboard
                )

        except ValueError as e:
            logger.error(f"Invalid task ID: {str(e)}")
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Неверный формат ID задачи"
            )
        except Exception as e:
            logger.error(f"Error showing task for removal: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="Ошибка при загрузке задачи"
            )

    def _confirm_removal(self, event):
        """Подтверждает снятие задачи с ревью"""
        try:
            task_id = int(event.data['callbackData'].split('_')[-1])
            chat_id = event.data['message']['chat']['chatId']
            user_id = event.data['from']['userId']

            with DatabaseManager().session() as db:
                task = db.query(Task).filter(
                    Task.id == task_id,
                    Task.user_id == user_id
                ).first()

                if task:
                    db.delete(task)
                    db.commit()

                    self.bot.bot.send_text(
                        chat_id=chat_id,
                        text="✅ Задача успешно снята с ревью!",
                        inline_keyboard_markup=self.keyboards.get_main_keyboard()
                    )
                else:
                    raise ValueError("Задача не найдена")

        except Exception as e:
            logger.error(f"Error confirming removal: {str(e)}", exc_info=True)
            self.bot.bot.send_text(
                chat_id=event.data['message']['chat']['chatId'],
                text="❌ Ошибка при снятии задачи"
            )

    def _cancel_removal(self, event):
        """Отменяет процесс снятия задачи"""
        self.bot.bot.send_text(
            chat_id=event.data['message']['chat']['chatId'],
            text="❌ Снятие задачи отменено",
            inline_keyboard_markup=self.keyboards.get_main_keyboard()
        )