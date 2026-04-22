import json
import logging
from collections import defaultdict
from pathlib import Path
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types
from database import async_session, get_user_profile
from services.achievements import ACHIEVEMENTS
from services.course_service import CourseService  #  Новый импорт

logger = logging.getLogger(__name__)

router = Router()
course_service = CourseService()  #  Инициализируем сервис

COURSES_JSON_PATH = Path(__file__).parent.parent / "data" / "courses.json"



@router.message(Command("profile"))
async def profile_command_handler(message: Message, state: FSMContext):
    """Обработчик команды /profile — сбрасывает состояние"""
    await state.clear()  # Сбрасываем любое активное состояние
    await profile_handler(message)

@router.message(F.text == "👤 Профиль")
async def profile_button_handler(message: Message, state: FSMContext):
    """Обработчик кнопки профиля — сбрасывает состояние"""
    await state.clear()  # Сбрасываем любое активное состояние
    await profile_handler(message)

@router.callback_query(F.data == "profile")
async def profile_callback(callback: types.CallbackQuery):
    """Обработчик кнопки 'Мой прогресс'"""
    # Перенаправляем на основной хендлер
    await profile_handler(callback.message)
    await callback.answer()

def _load_courses_index() -> dict[str, dict]:
    """Возвращает {course_id: {total_lessons, modules: {module_id: {title, lesson_ids}}}}."""
    try:
        with open(COURSES_JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    index = {}
    
    # Проверяем формат JSON: новый (с массивом courses) или старый
    if "courses" in data:
        # Новый формат: несколько курсов
        courses_list = data["courses"]
    else:
        # Старый формат: один курс
        courses_list = [data]
    
    for course in courses_list:
        course_id = course.get("course_id")
        if not course_id:
            continue
            
        modules = {}
        total = 0
        for module in course.get("modules", []):
            lesson_ids = [l["lesson_id"] for l in module.get("lessons", [])]
            modules[module["module_id"]] = {
                "title": module["title"],
                "lesson_ids": lesson_ids,
            }
            total += len(lesson_ids)
        
        index[course_id] = {
            "title": course.get("title", "Без названия"),
            "total_lessons": total,
            "modules": modules
        }
    
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

    # --- 🔥 Текущий урок (для быстрого продолжения) ---
    continue_section = []
    continue_keyboard = None
    
    if user.current_lesson_id:
        lesson = course_service.get_lesson(user.current_lesson_id)
        if lesson:
            continue_section = [
                f"",
                f"📍 <b>Следующий урок:</b> {lesson['title']}",
                f"<i>Модуль: {lesson['module_title']}</i>",
                f"Нажми кнопку ниже, чтобы продолжить:",
            ]
            continue_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Продолжить обучение", 
                                     callback_data=f"lesson_{user.current_lesson_id}")]
            ])

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
    
    # 🔥 Добавляем секцию текущего урока
    lines.extend(continue_section)

    lines += [
        f"",
        f"📊 <b>Прогресс по курсам:</b>",
    ] + progress_lines + [
        f"",
        f"🏅 <b>Достижения ({earned_count}/{total_count}):</b>",
    ] + achievement_lines + [
        f"",
        f"💡 <b>Команды:</b> /continue — продолжить, /help — справка"
    ]

    await message.answer(
        "\n".join(lines),
        reply_markup=continue_keyboard,  # Кнопка продолжения (если есть урок)
        parse_mode="HTML"
    )