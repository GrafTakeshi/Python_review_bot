# database/manager.py
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session
from config import Config
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(Config.DB_URL)
        self.Session = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        )
        logger.info("Database manager initialized")
        self._check_and_upgrade_db()

    def init_db(self):
        """Основной метод инициализации базы данных"""
        try:
            from bot.models.task import Base
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def _check_and_upgrade_db(self):
        """Проверяет и обновляет структуру БД при необходимости"""
        inspector = inspect(self.engine)

        if not inspector.has_table('tasks'):
            self.init_db()
            return

        # Проверка отсутствующих колонок
        existing_columns = [col['name'] for col in inspector.get_columns('tasks')]
        required_columns = [
            'id', 'user_id', 'creator', 'description',
            'youtrack_url', 'confluence_url', 'status',
            'approve_count', 'approved_by', 'reject_count',
            'rejected_by', 'created_at', 'completed_at'
        ]

        missing_columns = [col for col in required_columns if col not in existing_columns]

        if missing_columns:
            self._upgrade_db(missing_columns)

    def _upgrade_db(self, missing_columns):
        """Добавляет отсутствующие колонки в существующую таблицу"""
        with self.engine.connect() as conn:
            for column in missing_columns:
                try:
                    if column == 'reject_count':
                        conn.execute(text("ALTER TABLE tasks ADD COLUMN reject_count INTEGER DEFAULT 0"))
                    elif column == 'rejected_by':
                        conn.execute(text("ALTER TABLE tasks ADD COLUMN rejected_by JSON DEFAULT '[]'"))
                    # ... остальные условия для миграций
                except Exception as e:
                    logger.error(f"Ошибка добавления колонки {column}: {str(e)}")
                    raise
            conn.commit()

    def session(self):
        """Возвращает новую сессию БД"""
        return self.Session()