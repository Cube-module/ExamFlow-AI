from abc import ABC, abstractmethod

class LLMService(ABC):
    @abstractmethod
    async def explain_topic(self, topic: str, user_question: str) -> str:
        """Объяснить сложную тему простым языком"""
        pass

    @abstractmethod
    async def generate_tasks(self, topic: str, count: int = 3) -> list[dict]:
        """Сгенерировать задачи по теме. Возвращает список словарей: 
        [{'question': '...', 'answer': '...', 'hint': '...'}]"""
        pass

    @abstractmethod
    async def check_solution(self, task: dict, user_answer: str) -> dict:
        """Проверить решение. Возвращает: 
        {'is_correct': bool, 'feedback': '...', 'score': int}"""
        pass

# Пример реализации (заглушка)
class MockLLMService(LLMService):
    async def explain_topic(self, topic, user_question: str) -> str:
        question = user_question.lower()

        #ПСЕВДО-ИИ
        if "дискриминант" in question or "d =" in question:

            return "Дискриминант — это как сердце квадратного уравнения. Формула: D = b² - 4ac. Если он положительный — у уравнения два корня, если ноль — один, если отрицательный — корней нет (в реальных числах)." 
        
        if "корень" in question:
            return "Корень — это значение X, которое превращает уравнение в верное равенство (0=0)."
        
        return "Я пока учусь, но кажется, тут нужно применить формулу из теории. Попробуй спросить про дискриминант или коэффициенты."
    
    async def generate_tasks(self, topic, count=3):
        return [{"question": f"Задача по {topic} №{i}", "answer": "42", "hint": "Подумай"} for i in range(count)]
    
    async def check_solution(self, task, user_answer):
        is_correct = user_answer.strip() == task['answer']
        return {
            "is_correct": is_correct,
            "feedback": "Верно!" if is_correct else "Попробуй еще раз.",
            "score": 10 if is_correct else 0
        }

# Экземпляр сервиса
llm_service = MockLLMService() 