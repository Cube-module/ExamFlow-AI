from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from services.llm_interface import llm_service
from services.streak_service import update_streak
from database import get_user # функция получения юзера из БД

router = Router()

# Состояние для ожидания ответа на задачу
class LessonState(StatesGroup):
    answering = State()

@router.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: types.CallbackQuery):
    lesson_id = callback.data.split("_")[1]
    # Тут логика получения контента урока из БД/JSON
    content = "Теория про квадратные уравнения..."
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [{"text": "✅ Понял, дальше", "callback_data": f"next_lesson_{lesson_id}"},
         {"text": "❓ Не понял, объясни", "callback_data": f"ask_ai_{lesson_id}"}],
        [{"text": "📝 Хочу практику", "callback_data": f"practice_{lesson_id}"}]
    ])
    
    await callback.message.edit_text(content, reply_markup=keyboard)

@router.callback_query(F.data.startswith("ask_ai_"))
async def ask_ai_explanation(callback: types.CallbackQuery):
    topic = "Квадратные уравнения" # Получить из контекста урока
    await callback.message.edit_text("🤔 Спрашивай у ИИ, что именно непонятно (или нажми кнопку):")
    # Тут можно отправить состояние ожидания текста или дать шаблонные вопросы
    # При получении текста -> вызвать llm_service.explain_topic(...)

@router.callback_query(F.data.startswith("practice_"))
async def start_practice(callback: types.CallbackQuery, state: FSMContext):
    lesson_id = callback.data.split("_")[1]
    # Запрос к твоему модулю ИИ
    tasks = await llm_service.generate_tasks(topic="Quadratic", count=3)
    
    await state.update_data(tasks=tasks, current_task=0)
    await send_task(callback.message, tasks[0], state)

async def send_task(message: types.Message, task: dict, state: FSMContext):
    await message.answer(f"Задача: {task['question']}")
    await state.set_state(LessonState.answering)
    await state.update_data(current_solution_task=task)

@router.message(LessonState.answering)
async def check_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task = data.get('current_solution_task')
    
    # Проверка
    result = await llm_service.check_solution(task, message.text)
    
    if result['is_correct']:
        await message.answer(f"✅ {result['feedback']}")
        # Обновляем стрик и прогресс
        user = await get_user(message.from_user.id)
        await update_streak(user)
    else:
        await message.answer(f"❌ {result['feedback']}")
        # Предлагаем подсказку или повтор