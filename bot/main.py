import asyncio
import logging
import os

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db
from handlers import lessons, profile, start
from services.reminder_service import send_streak_reminders

TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()
dp.include_router(profile.router)
dp.include_router(lessons.router)
dp.include_router(start.router)


async def main():
    logging.basicConfig(level=logging.INFO)

    from services.llm_interface import llm_service
    logging.info("LLM сервис: %s", llm_service.__class__.__name__)

    if not TOKEN:
        logging.error("Не найден BOT_TOKEN в переменных окружения")
        raise RuntimeError("Не найден BOT_TOKEN в переменных окружения")

    await init_db()
    logging.info("База данных инициализирована")

    bot = Bot(token=TOKEN)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_streak_reminders, "cron", hour=19, minute=0, args=[bot])
    scheduler.start()
    logging.info("Планировщик напоминаний запущен")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
