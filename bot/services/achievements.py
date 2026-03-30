from sqlalchemy.ext.asyncio import AsyncSession

from database import User, UserAchievement

# Каталог всех достижений: id -> отображаемые данные
ACHIEVEMENTS: dict[str, dict] = {
    # Серии дней
    "streak_3":  {"emoji": "🔥", "title": "На разогреве",        "desc": "3 дня подряд"},
    "streak_7":  {"emoji": "⚡", "title": "Недельный воин",       "desc": "7 дней подряд"},
    "streak_30": {"emoji": "💎", "title": "Железная дисциплина",  "desc": "30 дней подряд"},
    # Прогресс по урокам
    "first_lesson":    {"emoji": "📖", "title": "Первый шаг",       "desc": "Первый урок пройден"},
    "first_module":    {"emoji": "🏆", "title": "Модуль пройден",   "desc": "Завершён первый модуль"},
    "course_complete": {"emoji": "🎓", "title": "Курс завершён",    "desc": "Все уроки курса пройдены"},
    # Качество
    "perfect_score":   {"emoji": "⭐", "title": "Идеальный результат", "desc": "Задача решена с первой попытки"},
}


def _already_has(user: User, achievement_id: str) -> bool:
    return any(a.achievement_id == achievement_id for a in user.achievements)


async def check_and_award(session: AsyncSession, user: User) -> list[str]:
    """Проверяет условия всех достижений и выдаёт новые. Возвращает список новых achievement_id."""
    awarded = []

    async def award(achievement_id: str) -> None:
        if not _already_has(user, achievement_id):
            user.achievements.append(UserAchievement(achievement_id=achievement_id))
            awarded.append(achievement_id)

    # --- Стрики ---
    if user.streak_count >= 3:
        await award("streak_3")
    if user.streak_count >= 7:
        await award("streak_7")
    if user.streak_count >= 30:
        await award("streak_30")

    # --- Прогресс по урокам ---
    completed = [p for p in user.progress if p.status == "completed"]

    if completed:
        await award("first_lesson")

    # Модуль пройден: все уроки из одного course_id+module завершены — упрощённо:
    # если завершено >= 2 урока в одном курсе считаем модуль пройденным
    from collections import Counter
    course_counts = Counter(p.course_id for p in completed if p.course_id)
    if any(count >= 2 for count in course_counts.values()):
        await award("first_module")

    # Курс завершён: проверяем через общее кол-во уроков — заглушка,
    # реальная проверка будет после подключения контента
    if any(count >= 4 for count in course_counts.values()):
        await award("course_complete")

    if awarded:
        await session.commit()

    return awarded
