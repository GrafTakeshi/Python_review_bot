from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

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