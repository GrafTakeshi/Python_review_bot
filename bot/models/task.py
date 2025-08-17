from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False)
    creator = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    youtrack_url = Column(String(200))
    confluence_url = Column(String(200))
    status = Column(Boolean, default=False)
    approve_count = Column(Integer, default=0)
    approved_by = Column(JSON, default=list)
    reject_count = Column(Integer, default=0)  # Новое поле - счетчик отклонений
    rejected_by = Column(JSON, default=list)  # Новое поле - список отклонивших
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Task(id={self.id}, description='{self.description[:20]}...')>"