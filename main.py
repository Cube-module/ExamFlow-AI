import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("<Приветствие пользователя>")


@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer("<Пояснение работы бота>")


async def main():
    logging.basicConfig(level=logging.INFO)

    if not TOKEN:
        logging.error("Не найден BOT_TOKEN в переменных окружения")
        raise RuntimeError("Не найден BOT_TOKEN в переменных окружения")

    bot = Bot(token=TOKEN)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())