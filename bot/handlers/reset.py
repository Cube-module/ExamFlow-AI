import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import delete
from database import async_session, get_or_create_user, UserProgress

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("reset"))
async def reset_progress(message: Message):
    """Запрос подтверждения сброса прогресса"""
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    
    # Исправление: используем current_lesson_id
    if not user.current_lesson_id:
        await message.answer("⚠️ Вы ещё не начали обучение.\n\nВыберите курс в /start")
        return
    
    # Получаем course_id из текущего урока
    from services.course_service import CourseService
    course_service = CourseService()
    lesson = course_service.get_lesson(user.current_lesson_id)
    
    if not lesson:
        await message.answer("⚠️ Текущий урок не найден.\n\nПопробуйте /start")
        return
    
    course_id = lesson.get("course_id")
    course = course_service.get_course_by_id(course_id)
    course_name = course.get("title", "текущего курса") if course else "текущего курса"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, сбросить", callback_data="reset_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="reset_cancel")
        ]
    ])
    
    await message.answer(
        f"⚠️ <b>Сбросить прогресс по курсу «{course_name}»?</b>\n\n"
        f"Все пройденные уроки будут отмечены как непройденные.\n"
        f"Достижения сохранятся.\n\n"
        f"<i>Это действие нельзя отменить.</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "reset_confirm")
async def confirm_reset(callback):
    """Подтверждение сброса"""
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        
        if user.current_lesson_id:
            # Получаем course_id из урока
            from services.course_service import CourseService
            course_service = CourseService()
            lesson = course_service.get_lesson(user.current_lesson_id)
            course_id = lesson.get("course_id") if lesson else None
            
            # Удаляем все записи прогресса по текущему курсу
            if course_id:
                await session.execute(
                    delete(UserProgress).where(
                        UserProgress.user_id == user.id,
                        UserProgress.course_id == course_id
                    )
                )
            
            # Сбрасываем текущий урок
            user.current_lesson_id = None
            await session.commit()
            
            logger.info(f"User {user.id} reset progress for course {course_id}")
    
    await callback.message.edit_text(
        "✅ <b>Прогресс сброшен!</b>\n\n"
        "Теперь ты можешь начать курс заново.\n\n"
        "Используй /continue для начала с первого урока.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "reset_cancel")
async def cancel_reset(callback):
    """Отмена сброса"""
    await callback.message.edit_text(
        "❌ Сброс прогресса отменён.\n\n"
        "Твой прогресс сохранён."
    )
    await callback.answer()