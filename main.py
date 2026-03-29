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
    welcome_text = f"""
Привет, {message.from_user.first_name}!

Я ExamFlow-AI – твой персональный помощник для подготовки к экзаменам!

Что я умею:
• Провожу тебя через структурированные курсы по подготовке к экзаменам
• Объясняю сложные темы простым языком
• Генерирую практические задачи для закрепления материала
• Помогаю поддерживать дисциплину через систему достижений и серий дней

Система мотивации:
• Серия дней – занимайся регулярно и не теряй прогресс!
• Достижения – получай бейджи за успехи
• Персональная статистика – отслеживай свой рост

Готов начать обучение? Используй /help для подробной информации о командах.

Удачи в подготовке! 
"""
    await message.answer(welcome_text)


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