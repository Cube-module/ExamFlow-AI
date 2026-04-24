import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import async_session, get_or_create_user
from services.llm_interface import llm_service
from services.streak_service import update_streak

from datetime import datetime, date, timezone
from sqlalchemy import select, func
from database import TaskHistory, UserProgress

logger = logging.getLogger(__name__)

router = Router()


class LessonState(StatesGroup):
    answering = State()
    asking_ai = State()


@router.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: types.CallbackQuery):
    lesson_id = callback.data.removeprefix("lesson_")
    # TODO: загрузить реальный контент урока из JSON по lesson_id
    content = "Теория про квадратные уравнения..."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Понял, дальше", callback_data=f"next_lesson_{lesson_id}"),
            InlineKeyboardButton(text="❓ Не понял, объясни", callback_data=f"ask_ai_{lesson_id}"),
        ],
        [
            InlineKeyboardButton(text="📝 Хочу практику", callback_data=f"practice_{lesson_id}"),
        ],
    ])

    await callback.message.edit_text(content, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("next_lesson_"))
async def next_lesson(callback: types.CallbackQuery, state: FSMContext):
    lesson_id = callback.data.removeprefix("next_lesson_")
    await state.clear()
    # TODO: определить следующий lesson_id по текущему и загрузить его контент
    await callback.message.answer("✅ Урок отмечен как пройденный!\n\nСледующий урок появится здесь после добавления контента.")
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)

        from sqlalchemy import select

        existing = await session.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.lesson_id == lesson_id,
                UserProgress.status == "completed"
            )
        )

        if existing.scalar_one_or_none() is None:
            session.add(UserProgress(
                user_id=user.id,
                course_id=user.selected_course,
                lesson_id=lesson_id,
                status="completed",
                completed_at=datetime.now(timezone.utc)
            ))

        await session.commit()
    await callback.answer()


@router.callback_query(F.data.startswith("ask_ai_"))
async def ask_ai_explanation(callback: types.CallbackQuery, state: FSMContext):
    lesson_id = callback.data.removeprefix("ask_ai_")
    await state.set_state(LessonState.asking_ai)
    await state.update_data(lesson_id=lesson_id)
    await callback.message.answer("🤔 Напиши, что именно непонятно, и я объясню:")
    await callback.answer()


@router.message(LessonState.asking_ai)
async def handle_ai_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lesson_id = data.get("lesson_id", "")
    # TODO: получать реальную тему урока из JSON по lesson_id
    topic = lesson_id

    explanation = await llm_service.explain_topic(topic=topic, user_question=message.text)
    await message.answer(f"💡 {explanation}")
    await state.clear()


@router.callback_query(F.data.startswith("practice_"))
async def start_practice(callback: types.CallbackQuery, state: FSMContext):
    lesson_id = callback.data.removeprefix("practice_")
    # TODO: передавать реальную тему урока из JSON по lesson_id
    tasks = await llm_service.generate_tasks(topic=lesson_id, count=3)

    if not tasks:
        await callback.message.answer("Не удалось загрузить задачи. Попробуй позже.")
        await callback.answer()
        return

    await state.update_data(tasks=tasks, current_task=0, lesson_id=lesson_id)
    await send_task(callback.message, tasks[0], state)
    await callback.answer()


async def send_task(message: types.Message, task: dict, state: FSMContext) -> None:
    await message.answer(f"Задача: {task['question']}")
    await state.set_state(LessonState.answering)
    await state.update_data(current_solution_task=task)


@router.message(LessonState.answering)
async def check_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task = data.get("current_solution_task")

    if task is None:
        await message.answer("Сессия истекла. Начни урок заново.")
        await state.clear()
        return

    result = await llm_service.check_solution(task, message.text)

    if result["is_correct"]:
        await message.answer(f"✅ {result['feedback']}")
        async with async_session() as session:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username)

            # сохраняем задачу
            session.add(TaskHistory(user_id=user.id))
            await session.commit()

            # обновляем серию
            await update_streak(session, user)

            # считаем задачи за сегодня
            today = date.today()
            start_of_day = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

            tasks_today = await session.scalar(
                select(func.count()).select_from(TaskHistory).where(
                    TaskHistory.user_id == user.id,
                    TaskHistory.created_at >= start_of_day
                )
            )

            # считаем уроки за сегодня
            lessons_today = await session.scalar(
                select(func.count()).select_from(UserProgress).where(
                    UserProgress.user_id == user.id,
                    UserProgress.status == "completed",
                    UserProgress.completed_at >= start_of_day
                )
            )

            lessons_today = lessons_today or 0

            # уведомление
            if (
                tasks_today == 5
                and lessons_today >= 1
                and (
                    user.last_daily_reward_date is None
                    or user.last_daily_reward_date.date() != today
                )
            ):
                await message.answer("🎉 Дневная норма выполнена! Серия продолжается. +1 день 🔥")

                user.last_daily_reward_date = datetime.now(timezone.utc)
                await session.commit()

        # Переходим к следующей задаче, если есть
        tasks = data.get("tasks", [])
        current_task_index = data.get("current_task", 0) + 1

        if current_task_index < len(tasks):
            await state.update_data(current_task=current_task_index)
            await send_task(message, tasks[current_task_index], state)
        else:
            await message.answer("🎉 Все задачи выполнены! Отличная работа!")
            await state.clear()
    else:
        await message.answer(f"❌ {result['feedback']}\n\nПопробуй ещё раз:")
