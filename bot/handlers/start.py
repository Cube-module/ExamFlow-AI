import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database import async_session, get_or_create_user

logger = logging.getLogger(__name__)

router = Router()

COURSES = {
    "📊 Математика ЕГЭ (Профиль)": """
📊 Математика ЕГЭ (Профильный уровень)

Курс включает:
• Алгебра и начала анализа
• Геометрия (планиметрия и стереометрия)
• Уравнения и неравенства
• Функции и графики
• Задачи с параметрами

Статус: В разработке 🚧
Скоро здесь появятся уроки и практические задания!
""",
    "💻 Информатика ЕГЭ": """
💻 Информатика ЕГЭ

Курс включает:
• Системы счисления
• Алгоритмизация и программирование
• Логика и комбинаторика
• Информационные модели
• Работа с файлами и базами данных

Статус: В разработке 🚧
Скоро здесь появятся уроки и практические задания!
""",
    "📐 Математика ОГЭ": """
📐 Математика ОГЭ

Курс включает:
• Арифметика и алгебра
• Геометрия на плоскости
• Функции и графики
• Текстовые задачи
• Вероятность и статистика

Статус: В разработке 🚧
Скоро здесь появятся уроки и практические задания!
""",
    "🖥 Информатика ОГЭ": """
🖥 Информатика ОГЭ

Курс включает:
• Основы алгоритмизации
• Системы счисления (базовый уровень)
• Работа с электронными таблицами
• Логические выражения
• Основы программирования

Статус: В разработке 🚧
Скоро здесь появятся уроки и практические задания!
""",
}

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Математика ЕГЭ (Профиль)")],
        [KeyboardButton(text="💻 Информатика ЕГЭ")],
        [KeyboardButton(text="📐 Математика ОГЭ")],
        [KeyboardButton(text="🖥 Информатика ОГЭ")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True,
)

HELP_TEXT = """
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


@router.message(CommandStart())
async def start(message: Message):
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )
        is_new = user.selected_course is None
        logger.info("User %s: %s", message.from_user.id, "registered" if is_new else "returned")

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
    await message.answer(welcome_text, reply_markup=MAIN_KEYBOARD)


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message):
    await message.answer(HELP_TEXT)


@router.message(F.text.in_(COURSES))
async def course_handler(message: Message):
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        user.selected_course = message.text
        await session.commit()
        logger.info("User %s selected course: %s", message.from_user.id, message.text)

    await message.answer(COURSES[message.text])


@router.message(StateFilter(None))
async def fallback_handler(message: Message):
    await message.answer(
        "Не понял команду. Выбери курс из меню или напиши /help.",
        reply_markup=MAIN_KEYBOARD,
    )
