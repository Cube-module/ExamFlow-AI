#ЛОГИКА СЕРИИ ДНЕЙ
from datetime import datetime, timedelta
from database import User, SessionLocal # SessionLocal - сессия БД

async def update_streak(user: User):
    """Вызывать при любом полезном действии (урок, задача)"""
    now = datetime.utcnow()
    last_activity = user.last_activity_date
    
    # Разница в днях
    delta = now.date() - last_activity.date()
    
    if delta.days == 0:
        # Сегодня уже занимались, стрик не меняем, просто обновляем время
        user.last_activity_date = now
    elif delta.days == 1:
        # Вчерашний день был пропущен? Нет, это новый день подряд
        user.streak_count += 1
        user.last_activity_date = now
        # Тут можно проверить ачивки на серию
    else:
        # Пропуск >= 2 дней
        if user.freeze_available:
            user.freeze_available = False # Тратим заморозку
            user.streak_count += 1 # Сохраняем стрик
            # Уведомить пользователя, что заморозка сработала
        else:
            user.streak_count = 0 # Сгорание
            user.last_activity_date = now
            # Уведомить о потере серии
    
    await commit_changes()