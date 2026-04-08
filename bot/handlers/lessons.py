import logging
from datetime import datetime

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import async_session, get_or_create_user, UserProgress
from services.llm_interface import llm_service
from services.streak_service import update_streak
from services.course_service import CourseService  # Новый импорт

logger = logging.getLogger(__name__)

router = Router()
course_service = CourseService()  #  Инициализируем сервис курсов


class LessonState(StatesGroup):
    answering = State()
    asking_ai = State()


@router.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: types.CallbackQuery):
    """ [EF-002] Загружает реальный контент урока из courses.json"""
    lesson_id = callback.data.removeprefix("lesson_")
    
    # Загружаем урок из JSON
    lesson = course_service.get_lesson(lesson_id)
    if not lesson:
        await callback.answer("❌ Урок не найден", show_alert=True)
        return
    
    # Формируем текст сообщения
    text = f"📚 <b>{lesson['title']}</b>\n"
    text += f"<i>Модуль: {lesson['module_title']}</i>\n\n"
    text += lesson["content"]
    text += f"\n\n💡 <b>Главное за 1 минуту:</b>\n{lesson['summary']}"
    
    # Кнопки навигации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Понял, дальше", callback_data=f"next_lesson_{lesson_id}"),
            InlineKeyboardButton(text="❓ Не понял", callback_data=f"ask_ai_{lesson_id}"),
        ],
        [
            InlineKeyboardButton(text="📝 Хочу практику", callback_data=f"practice_{lesson_id}"),
        ],
    ])
    
    # 🔥 Кнопка видео (если есть ресурсы)
    if lesson.get("video_resources"):
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🎥 Видео по теме", callback_data=f"videos_{lesson_id}")
        ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("next_lesson_"))
async def next_lesson(callback: types.CallbackQuery, state: FSMContext):
    """ [EF-003] Переход к следующему уроку + сохранение прогресса"""
    current_lesson_id = callback.data.removeprefix("next_lesson_")
    await state.clear()
    
    # 1. Сохраняем прогресс: текущий урок = completed
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        
        # Ищем или создаём запись прогресса
        progress = await session.get(UserProgress, (user.id, current_lesson_id))
        if not progress:
            progress = UserProgress(
                user_id=user.id,
                lesson_id=current_lesson_id,
                status="in_progress"
            )
            session.add(progress)
        
        # Обновляем статус
        progress.status = "completed"
        progress.score = max(progress.score or 0, 10)
        progress.completed_at = datetime.utcnow()
        
        await session.commit()
        
        # Обновляем стрик (геймификация)
        await update_streak(session, user)
    
    # 2. Находим следующий урок
    next_lesson_id = course_service.get_next_lesson_id(current_lesson_id)
    
    if not next_lesson_id:
        # Курс завершён!
        await callback.message.edit_text(
            "🎉 <b>Поздравляем! Курс завершён!</b>\n\n"
            "Ты прошёл все уроки. Теперь можешь:\n"
            "• Повторить сложные темы в профиле\n"
            "• Пройти курс заново для закрепления",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="profile")],
                [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="course_restart")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # 3. Загружаем и показываем следующий урок
    lesson = course_service.get_lesson(next_lesson_id)
    if not lesson:
        await callback.answer("❌ Следующий урок не найден", show_alert=True)
        return
    
    text = f"📚 <b>{lesson['title']}</b>\n"
    text += f"<i>Модуль: {lesson['module_title']}</i>\n\n"
    text += lesson["content"]
    text += f"\n\n💡 <b>Главное за 1 минуту:</b>\n{lesson['summary']}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Понял, дальше", callback_data=f"next_lesson_{next_lesson_id}"),
            InlineKeyboardButton(text="❓ Не понял", callback_data=f"ask_ai_{next_lesson_id}"),
        ],
        [
            InlineKeyboardButton(text="📝 Хочу практику", callback_data=f"practice_{next_lesson_id}"),
        ],
    ])
    
    if lesson.get("video_resources"):
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🎥 Видео по теме", callback_data=f"videos_{next_lesson_id}")
        ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ask_ai_"))
async def ask_ai_explanation(callback: types.CallbackQuery, state: FSMContext):
    """ [EF-002] Передаёт реальную тему урока в LLM, а не сырой ID"""
    lesson_id = callback.data.removeprefix("ask_ai_")
    
    # Получаем понятную тему для ИИ
    topic = course_service.get_lesson_topic(lesson_id)
    
    await state.set_state(LessonState.asking_ai)
    await state.update_data(lesson_id=lesson_id, topic=topic)
    
    await callback.message.answer(
        f"🤔 <b>Тема:</b> {topic}\n\nНапиши, что именно непонятно:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(LessonState.asking_ai)
async def handle_ai_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lesson_id = data.get("lesson_id", "")
    topic = data.get("topic", lesson_id)  # 🔥 Используем реальную тему
    
    explanation = await llm_service.explain_topic(
        topic=topic,
        user_question=message.text
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩ Назад к уроку", callback_data=f"lesson_{lesson_id}")]
    ])
    
    await message.answer(
        f"🤖 <b>Объяснение:</b>\n\n{explanation}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.clear()


@router.callback_query(F.data.startswith("practice_"))
async def start_practice(callback: types.CallbackQuery, state: FSMContext):
    """ [EF-002] Генерирует задачи по реальной теме урока"""
    lesson_id = callback.data.removeprefix("practice_")
    
    # Получаем понятную тему для генерации задач
    topic = course_service.get_lesson_topic(lesson_id)
    
    tasks = await llm_service.generate_tasks(topic=topic, count=3)
    
    if not tasks:
        await callback.message.answer("⚠️ Не удалось загрузить задачи. Попробуй позже.")
        await callback.answer()
        return
    
    await state.update_data(
        tasks=tasks,
        current_task=0,
        lesson_id=lesson_id,
        topic=topic  # Сохраняем тему для отладки
    )
    await send_task(callback.message, tasks[0], state)
    await callback.answer()


async def send_task(message: types.Message, task: dict, state: FSMContext) -> None:
    """Вспомогательная функция: отправляет задачу пользователю"""
    await message.answer(f"📝 <b>Задача:</b>\n{task['question']}", parse_mode="HTML")
    await state.set_state(LessonState.answering)
    await state.update_data(current_solution_task=task)


@router.message(LessonState.answering)
async def check_answer(message: types.Message, state: FSMContext):
    """Проверяет ответ пользователя и даёт обратную связь"""
    data = await state.get_data()
    task = data.get("current_solution_task")
    
    if task is None:
        await message.answer("⚠️ Сессия истекла. Начни урок заново.")
        await state.clear()
        return
    
    result = await llm_service.check_solution(task, message.text)
    
    if result["is_correct"]:
        await message.answer(f"✅ {result['feedback']}")
        
        # Обновляем стрик только за правильные ответы
        async with async_session() as session:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
            await update_streak(session, user)
        
        # Переходим к следующей задаче
        tasks = data.get("tasks", [])
        current_task_index = data.get("current_task", 0) + 1
        
        if current_task_index < len(tasks):
            await state.update_data(current_task=current_task_index)
            await send_task(message, tasks[current_task_index], state)
        else:
            await message.answer("🎉 Все задачи выполнены! Отличная работа!")
            await state.clear()
    else:
        await message.answer(
            f"❌ {result['feedback']}\n\n"
            f"💡 Подсказка: {task.get('hint', 'Попробуй ещё раз')}\n"
            f"Попробуй ещё раз:"
        )


@router.callback_query(F.data.startswith("videos_"))
async def show_videos(callback: types.CallbackQuery):
    """🔥 Показывает список видео по теме урока"""
    lesson_id = callback.data.removeprefix("videos_")
    lesson = course_service.get_lesson(lesson_id)
    
    if not lesson or not lesson.get("video_resources"):
        await callback.answer("🔜 Видео пока добавляются", show_alert=True)
        return
    
    videos = lesson["video_resources"]
    text = f"🎬 <b>Видео по теме:</b> {lesson['title']}\n\n"
    
    for i, video in enumerate(videos, 1):
        # Эмодзи платформы
        platform = video.get("platform", "")
        if "Bobr" in platform:
            emoji = "🟠"
            note = " ⚡ без VPN"
        elif "YouTube" in platform:
            emoji = "🔴"
            note = ""
        else:
            emoji = "📺"
            note = ""
        
        text += f"{i}. {emoji} <b>{video['title']}</b> ({video.get('duration', '?')}){note}\n"
        text += f"   Платформа: {platform}\n"
        text += f"   🔗 <a href=\"{video['url']}\">Смотреть</a>\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩ Назад к уроку", callback_data=f"lesson_{lesson_id}")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True  # Не грузить превью ссылок
    )
    await callback.answer()