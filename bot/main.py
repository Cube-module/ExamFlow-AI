import asyncio
import logging
import os

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

from aiogram import Bot, Dispatcher

from database import init_db
from handlers import lessons, profile, start

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
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
