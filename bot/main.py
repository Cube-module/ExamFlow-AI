import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

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

Выбери курс, чтобы начать обучение:
"""

    # Создаем клавиатуру с курсами
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Математика ЕГЭ (Профиль)")],
            [KeyboardButton(text="💻 Информатика ЕГЭ")],
            [KeyboardButton(text="📐 Математика ОГЭ")],
            [KeyboardButton(text="🖥 Информатика ОГЭ")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )

    await message.answer(welcome_text, reply_markup=keyboard)


@dp.message(Command("help"))
async def help_handler(message: Message):
    help_text = """
📚 Доступные команды:

/start - Начать работу с ботом и выбрать курс
/help - Показать эту справку

🎓 Как работать с ботом:
1. Выбери курс из предложенных кнопок
2. Проходи уроки последовательно
3. Решай задачи для закрепления материала
4. Поддерживай серию дней для мотивации

Удачи в обучении!
"""
    await message.answer(help_text)


@dp.message(lambda message: message.text == "📊 Математика ЕГЭ (Профиль)")
async def math_ege_profile(message: Message):
    course_info = """
📊 Математика ЕГЭ (Профильный уровень)

Курс включает:
• Алгебра и начала анализа
• Геометрия (планиметрия и стереометрия)
• Уравнения и неравенства
• Функции и графики
• Задачи с параметрами

Статус: В разработке 🚧
Скоро здесь появятся уроки и практические задания!
"""
    await message.answer(course_info)


@dp.message(lambda message: message.text == "💻 Информатика ЕГЭ")
async def informatics_ege(message: Message):
    course_info = """
💻 Информатика ЕГЭ

Курс включает:
• Системы счисления
• Алгоритмизация и программирование
• Логика и комбинаторика
• Информационные модели
• Работа с файлами и базами данных

Статус: В разработке 🚧
Скоро здесь появятся уроки и практические задания!
"""
    await message.answer(course_info)


@dp.message(lambda message: message.text == "📐 Математика ОГЭ")
async def math_oge(message: Message):
    course_info = """
📐 Математика ОГЭ

Курс включает:
• Арифметика и алгебра
• Геометрия на плоскости
• Функции и графики
• Текстовые задачи
• Вероятность и статистика

Статус: В разработке 🚧
Скоро здесь появятся уроки и практические задания!
"""
    await message.answer(course_info)


@dp.message(lambda message: message.text == "🖥 Информатика ОГЭ")
async def informatics_oge(message: Message):
    course_info = """
🖥 Информатика ОГЭ

Курс включает:
• Основы алгоритмизации
• Системы счисления (базовый уровень)
• Работа с электронными таблицами
• Логические выражения
• Основы программирования

Статус: В разработке 🚧
Скоро здесь появятся уроки и практические задания!
"""
    await message.answer(course_info)


@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def help_button_handler(message: Message):
    await help_handler(message)


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