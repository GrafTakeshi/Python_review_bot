from vkteams.types import InlineKeyboardMarkup, KeyboardButton

class KeyboardBuilder:
    def get_main_keyboard(self):
        keyboard = InlineKeyboardMarkup(buttons_in_row=2)
        keyboard.row(
            KeyboardButton(
                text="На ревью",
                callbackData="on_review",
                style="primary"
            ),
            KeyboardButton(
                text="Мои задачи",
                callbackData="my_tasks",
                style="secondary"
            )
        )
        keyboard.row(
            KeyboardButton(
                text="Снять с ревью",
                callbackData="remove_review",
                style="attention"
            ),
            KeyboardButton(
                text="Провести ревью",
                callbackData="do_review",
                style="primary"
            )
        )
        return keyboard

    def get_confirmation_keyboard(self):
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            KeyboardButton(
                text="Подтвердить",
                callbackData="confirm_task",
                style="primary"
            ),
            KeyboardButton(
                text="Отменить",
                callbackData="cancel_task",
                style="attention"
            )
        )
        return keyboard

    def get_task_keyboard(self, task_id):
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            KeyboardButton(
                text="Одобрить",
                callbackData=f"approve_task_{task_id}",
                style="primary"
            ),
            KeyboardButton(
                text="На доработку",
                callbackData=f"request_revision_{task_id}",
                style="attention"
            )
        )
        return keyboard