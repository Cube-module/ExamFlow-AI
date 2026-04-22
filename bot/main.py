import asyncio
import logging
import os
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services.reminder_service import send_streak_reminders
from handlers import lessons, profile, start, reset

import traceback
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.triggers.cron import CronTrigger


from database import async_session, User, init_db


# Теперь можно читать

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

dp = Dispatcher()


from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import async_session, User
from services.streak_service import check_streak_loss

async def send_streak_reminders(bot):
    """Ежедневная проверка серий (в 22:00)"""
    async with async_session() as session:
        users = await session.execute(select(User))
        users = users.scalars().all()
        
        for user in users:
            if user.streak_count > 0:
                lost = await check_streak_loss(session, user)
                if lost:
                    await bot.send_message(
                        user.telegram_id,
                        "Твоя серия сгорела! Начни заниматься снова, чтобы не потерять прогресс."
                    )


load_dotenv()


logger = logging.getLogger(__name__)

# Исправленная сигнатура для aiogram 3.x
@dp.errors()
async def error_handler(update, exception: Exception):
    """Глобальный обработчик необработанных исключений"""
    
    # Логируем полный traceback
    full_traceback = traceback.format_exception(type(exception), exception, exception.__traceback__)
    logger.error("🚨 Ошибка бота:\n%s", "".join(full_traceback))
    
    # Отправляем уведомление админу, если задан ADMIN_CHAT_ID
    if ADMIN_CHAT_ID:
        try:
            error_text = (
                f"🚨 <b>Ошибка бота</b>\n\n"
                f"<b>Тип:</b> {type(exception).__name__}\n"
                f"<b>Сообщение:</b> {str(exception)[:500]}\n"
                f"<b>Update ID:</b> {getattr(update, 'update_id', 'N/A')}\n\n"
                f"<i>Полный traceback в логах.</i>"
            )
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=error_text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error("Не удалось отправить уведомление админу: %s", e)
    
    return True


async def main():
    logging.basicConfig(level=logging.INFO)

    from services.llm_interface import llm_service
    logging.info("LLM сервис: %s", llm_service.__class__.__name__)

    if not TOKEN:
        logging.error("Не найден BOT_TOKEN в переменных окружения")
        raise RuntimeError("Не найден BOT_TOKEN в переменных окружения")

    await init_db()
    logging.info("База данных инициализирована")

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Регистрируем роутеры
    dp.include_router(profile.router)
    dp.include_router(reset.router)  # Добавлен reset
    dp.include_router(lessons.router)
    dp.include_router(start.router)

    

    # Планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_streak_reminders,
        "cron",
        hour=19,
        minute=0,
        args=[bot],
        id="streak_reminders",
        replace_existing=True
    )
    scheduler.start()
    logging.info("Планировщик напоминаний запущен")

    try:
        logging.info("Бот запущен...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logging.info("Сессия бота закрыта")


if __name__ == "__main__":
    asyncio.run(main())
