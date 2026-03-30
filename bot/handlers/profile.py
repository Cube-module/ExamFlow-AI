import json
import logging
from collections import defaultdict
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database import async_session, get_user_profile
from services.achievements import ACHIEVEMENTS

logger = logging.getLogger(__name__)

router = Router()

COURSES_JSON_PATH = Path(__file__).parent.parent / "data" / "courses.json"


def _load_courses_index() -> dict[str, dict]:
    """Возвращает {course_id: {total_lessons, modules: {module_id: {title, lesson_ids}}}}."""
    try:
        with open(COURSES_JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    index = {}
    course_id = data["course_id"]
    modules = {}
    total = 0
    for module in data.get("modules", []):
        lesson_ids = [l["lesson_id"] for l in module.get("lessons", [])]
        modules[module["module_id"]] = {
            "title": module["title"],
            "lesson_ids": lesson_ids,
        }
        total += len(lesson_ids)
    index[course_id] = {"title": data["title"], "total_lessons": total, "modules": modules}
    return index


def _streak_bar(streak: int) -> str:
    if streak == 0:
        return "0 дней"
    fire = min(streak // 3 + 1, 5)
    return "🔥" * fire + f" {streak} дн."


def _progress_bar(done: int, total: int) -> str:
    if total == 0:
        return "—"
    pct = done / total
    filled = round(pct * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{bar} {done}/{total}"


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    async with async_session() as session:
        user = await get_user_profile(session, message.from_user.id)

    if user is None:
        await message.answer("Профиль не найден. Напиши /start, чтобы зарегистрироваться.")
        return

    courses_index = _load_courses_index()

    # --- Серия дней ---
    streak_line = _streak_bar(user.streak_count)
    freeze_line = "❄️ Заморозка: доступна" if user.freeze_available else ""

    # --- Прогресс по курсам ---
    completed_ids: set[str] = {
        p.lesson_id for p in user.progress if p.status == "completed"
    }
    # Группируем выполненные уроки по course_id
    completed_by_course: dict[str, set[str]] = defaultdict(set)
    for p in user.progress:
        if p.status == "completed" and p.course_id:
            completed_by_course[p.course_id].add(p.lesson_id)

    progress_lines = []
    for course_id, course_data in courses_index.items():
        done_total = len(completed_by_course.get(course_id, set()))
        total = course_data["total_lessons"]
        progress_lines.append(f"\n📚 {course_data['title']}")
        for mod_id, mod_data in course_data["modules"].items():
            done_mod = sum(
                1 for lid in mod_data["lesson_ids"]
                if lid in completed_by_course.get(course_id, set())
            )
            total_mod = len(mod_data["lesson_ids"])
            bar = _progress_bar(done_mod, total_mod)
            progress_lines.append(f"  {mod_data['title']}: {bar}")
        overall_pct = int(done_total / total * 100) if total else 0
        progress_lines.append(f"  Итого: {done_total}/{total} ({overall_pct}%)")

    if not progress_lines:
        progress_lines = ["  Ещё не начато — выбери курс и приступай!"]

    # --- Достижения ---
    earned_ids = {a.achievement_id for a in user.achievements}
    achievement_lines = []
    for ach_id, ach in ACHIEVEMENTS.items():
        if ach_id in earned_ids:
            achievement_lines.append(f"  ✅ {ach['emoji']} {ach['title']} — {ach['desc']}")
        else:
            achievement_lines.append(f"  ⬜ {ach['emoji']} {ach['title']} — {ach['desc']}")

    earned_count = len(earned_ids)
    total_count = len(ACHIEVEMENTS)

    # --- Сборка сообщения ---
    lines = [
        f"👤 <b>Личный кабинет</b>",
        f"",
        f"🔥 <b>Серия дней:</b> {streak_line}",
    ]
    if freeze_line:
        lines.append(freeze_line)

    lines += [
        f"",
        f"📊 <b>Прогресс по курсам:</b>",
    ] + progress_lines + [
        f"",
        f"🏅 <b>Достижения ({earned_count}/{total_count}):</b>",
    ] + achievement_lines

    await message.answer("\n".join(lines), parse_mode="HTML")
