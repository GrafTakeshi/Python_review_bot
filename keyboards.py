from vkteams.types import InlineKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(buttons_in_row=2)
    keyboard.row(KeyboardButton(text="На ревью", callbackData="on_review", style="primary"))
    keyboard.row(KeyboardButton(text="Мои задачи", callbackData="my_tasks", style="secondary"))
    keyboard.row(
        KeyboardButton(text="Снять с ревью", callbackData="remove_review", style="attention"),
        KeyboardButton(text="Провести ревью", callbackData="do_review", style="primary")
    )
    return keyboard

def get_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        KeyboardButton(text="Подтвердить", callbackData="confirm_task", style="primary"),
        KeyboardButton(text="Отменить", callbackData="cancel_task", style="attention")
    )
    return keyboard

def get_yes_no_keyboard(task_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        KeyboardButton(text="Да", callbackData=f"confirm_remove_{task_id}", style="primary"),
        KeyboardButton(text="Нет", callbackData="cancel_remove", style="attention")
    )
    return keyboard

def get_task_keyboard(task_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        KeyboardButton(text="Одобрить", callbackData=f"approve_task_{task_id}", style="primary"),
        KeyboardButton(text="На доработку", callbackData=f"request_revision_{task_id}", style="attention")
    )
    return keyboard

def get_review_tasks_keyboard(tasks):
    keyboard = InlineKeyboardMarkup(buttons_in_row=1)
    for task in tasks:
        keyboard.row(
            KeyboardButton(
                text=f"Задача #{task.id}: {task.description[:50]}...",
                callbackData=f"review_task_{task.id}"
            )
        )
    return keyboard