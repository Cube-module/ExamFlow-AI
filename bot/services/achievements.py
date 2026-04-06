import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from database import User, UserAchievement

COURSES_JSON_PATH = Path(__file__).parent.parent / "data" / "courses.json"

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


def _load_courses() -> dict:
    try:
        with open(COURSES_JSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


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
        user.freeze_available = True
    if user.streak_count >= 30:
        await award("streak_30")

    # --- Прогресс по урокам ---
    completed = [p for p in user.progress if p.status == "completed"]

    if completed:
        await award("first_lesson")

    # Множество пройденных lesson_id по каждому курсу
    completed_by_course: dict[str, set[str]] = {}
    for p in completed:
        if p.course_id:
            completed_by_course.setdefault(p.course_id, set()).add(p.lesson_id)

    # Проверка модулей и курса по реальной структуре courses.json
    courses_data = _load_courses()
    if courses_data:
        course_id = courses_data.get("course_id")
        modules = courses_data.get("modules", [])
        completed_ids = completed_by_course.get(course_id, set())

        all_modules_done = True
        for module in modules:
            module_lesson_ids = {lesson["lesson_id"] for lesson in module.get("lessons", [])}
            if module_lesson_ids and module_lesson_ids.issubset(completed_ids):
                await award("first_module")
            else:
                all_modules_done = False

        if modules and all_modules_done:
            await award("course_complete")

    if awarded:
        await session.commit()

    return awarded
