from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True)
    username = Column(String)
    
    # Геймификация
    streak_count = Column(Integer, default=0)
    last_activity_date = Column(DateTime, default=datetime.utcnow)
    freeze_available = Column(Boolean, default=False) # Заморозка стрика
    
    progress = relationship("UserProgress", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")

class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    lesson_id = Column(String) # ID урока из курса
    status = Column(String) # 'locked', 'in_progress', 'completed'
    score = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="progress")

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(String) # ID ачивки (например, 'first_blood')
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="achievements")