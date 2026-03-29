import asyncio
import logging
import os

from aiogram import Bot, Dispatcher

from database import init_db
from handlers import lessons, start

TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()
dp.include_router(start.router)
dp.include_router(lessons.router)


async def main():
    logging.basicConfig(level=logging.INFO)

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
