import os
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship, selectinload

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///examflow.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True)
    username = Column(String)
    
    # Геймификация
    streak_count = Column(Integer, default=0)
    last_activity_date = Column(DateTime, default=datetime.utcnow)
    freeze_available = Column(Boolean, default=False)
    
    # Прогресс курса
    selected_course = Column(String, nullable=True)
    current_lesson_id = Column(String, nullable=True)  # ← Добавь это
    
    progress = relationship("UserProgress", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    lesson_id = Column(String)
    status = Column(String)  # 'locked', 'in_progress', 'completed'
    score = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    course_id = Column(String, nullable=True)  # Если нужно

    user = relationship("User", back_populates="progress")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(String)
    unlocked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="achievements")


# bot/database.py
async def save_user_progress(user_id: int, lesson_id: str, status: str, score: int):
    async with SessionLocal() as session:
        progress = await session.get(UserProgress, {"user_id": user_id, "lesson_id": lesson_id})
        if not progress:
            progress = UserProgress(user_id=user_id, lesson_id=lesson_id)
        progress.status = status
        progress.score = score
        progress.completed_at = datetime.utcnow() if status == "completed" else None
        session.add(progress)
        await session.commit()

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Миграция: добавить колонки, которых может не быть в старой БД
        for column_sql in [
            "ALTER TABLE users ADD COLUMN last_reminder_date DATETIME",
            "ALTER TABLE users ADD COLUMN current_lesson_id VARCHAR",
        ]:
            try:
                await conn.exec_driver_sql(column_sql)
            except Exception:
                pass  # колонка уже существует


from sqlalchemy import select
from sqlalchemy.orm import selectinload  # Импортируем

async def get_user_profile(session, telegram_id: int):
    """Получает пользователя с прогрессом и достижениями"""
    result = await session.execute(
        select(User)
        .where(User.telegram_id == str(telegram_id))  # Преобразуем в строку
        .options(
            selectinload(User.progress),      # Загружаем прогресс
            selectinload(User.achievements)   # Загружаем достижения
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == str(telegram_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=str(telegram_id),
            username=username,
        )
        session.add(user)
        await session.commit()

    return user


