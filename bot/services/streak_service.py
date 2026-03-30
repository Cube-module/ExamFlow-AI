from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from database import User
from services.achievements import check_and_award


async def update_streak(session: AsyncSession, user: User) -> None:
    """Вызывать при любом полезном действии (урок, задача)."""
    now = datetime.now(timezone.utc)
    last_activity = user.last_activity_date

    if last_activity is None:
        user.streak_count = 1
        user.last_activity_date = now
        await session.commit()
        return

    # Приводим last_activity к aware datetime, если хранится naive
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    delta = now.date() - last_activity.date()

    if delta.days == 0:
        # Уже занимались сегодня — просто обновляем время
        user.last_activity_date = now
    elif delta.days == 1:
        # Новый день подряд
        user.streak_count += 1
        user.last_activity_date = now
    else:
        # Пропуск >= 2 дней
        if user.freeze_available:
            user.freeze_available = False  # тратим заморозку, стрик сохраняется
        else:
            user.streak_count = 0  # стрик сгорает
        user.last_activity_date = now

    await session.commit()
    await check_and_award(session, user)
