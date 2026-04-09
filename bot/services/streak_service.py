from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from database import User

async def update_streak(session: AsyncSession, user: User):
    """
    Обновляет серию дней при активности пользователя.
    Вызывать после каждого завершённого урока/задачи.
    """
    now = datetime.utcnow()
    last_activity = user.last_activity_date or now
    
    # Разница в днях
    delta_days = (now.date() - last_activity.date()).days
    
    if delta_days == 0:
        # Сегодня уже занимались — просто обновляем время
        user.last_activity_date = now
    elif delta_days == 1:
        # Новый день подряд — увеличиваем серию
        user.streak_count += 1
        user.last_activity_date = now
    else:
        # Пропуск >= 2 дней
        if user.freeze_available:
            # Тратим заморозку
            user.freeze_available = False
            user.streak_count += 1
            user.last_activity_date = now
            # Можно отправить уведомление: "Заморозка спасла твою серию!"
        else:
            # Сгорание серии
            user.streak_count = 0
            user.last_activity_date = now
            # Можно отправить уведомление: "Серия сгорела! Начинай заново!"
    
    await session.commit()


async def check_streak_loss(session: AsyncSession, user: User) -> bool:
    """
    Проверка: потерял ли пользователь серию за вчерашний день.
    Вызывать планировщиком раз в сутки.
    Возвращает True, если серия сгорела.
    """
    now = datetime.utcnow()
    last_activity = user.last_activity_date or now
    delta_days = (now.date() - last_activity.date()).days
    
    if delta_days >= 2:
        if user.freeze_available:
            user.freeze_available = False
            user.streak_count = 0
        else:
            user.streak_count = 0
        user.last_activity_date = now
        await session.commit()
        return True
    
    return False


async def grant_freeze(session: AsyncSession, user: User, count: int = 1):
    """Выдать пользователю заморозку серии"""
    user.freeze_available = True
    # Можно хранить несколько: user.freeze_count += count
    await session.commit()