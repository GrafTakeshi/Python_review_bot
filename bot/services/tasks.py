from datetime import datetime

from bot.models.task import Task
from database.manager import DatabaseManager
import logging

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self):
        self.db = DatabaseManager()

    def create_task(self, db_session, task_data):
        """Создает задачу с проверкой данных"""
        try:
            if not task_data.get('creator'):
                task_data['creator'] = 'Unknown'  # Значение по умолчанию

            task = Task(**task_data)
            db_session.add(task)
            db_session.commit()
            return task

        except Exception as e:
            db_session.rollback()
            logger.error(f"Ошибка создания задачи: {str(e)}")
            raise


    def get_pending_tasks(self):
        try:
            with self.db.session() as session:
                return session.query(Task).filter_by(status=False).all()
        except Exception as e:
            logger.error(f"Error getting tasks: {str(e)}")
            return []

    def get_user_tasks(self, db, user_id):
        """Получает все задачи пользователя"""
        return db.query(Task).filter(
            Task.user_id == user_id,
            Task.status == False
        ).all()

    def get_reviewable_tasks(self, db, user_id):
        """Получает задачи для ревью, исключая свои и отклоненные/одобренные пользователем"""
        return db.query(Task).filter(
            Task.status == False,
            Task.user_id != user_id,
            ~Task.rejected_by.contains([user_id]),  # Исключаем отклоненные пользователем
            ~Task.approved_by.contains([user_id])   # Исключаем уже одобренные
        ).all()

    def get_task(self, db, task_id):
        return db.query(Task).filter()

    def get_task_for_removal(self, db, task_id, user_id):
        """Получает задачу для снятия с проверкой владельца"""
        return db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == user_id
        ).first()