# bot/services/course_service.py
import json
from pathlib import Path
from typing import Optional

class CourseService:
    def __init__(self, courses_path: str = "bot/data/courses.json"):
        self.courses_path = Path(courses_path)
        self._cache: Optional[dict] = None
    
    def _load_courses(self) -> dict:
        """Загружает курсы из JSON (с кэшированием)"""
        if self._cache is None:
            with open(self.courses_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
        return self._cache
    
    def get_lesson(self, lesson_id: str) -> Optional[dict]:
        """Находит урок по ID в любом модуле курса"""
        courses = self._load_courses()
        for module in courses.get("modules", []):
            for lesson in module.get("lessons", []):
                if lesson["lesson_id"] == lesson_id:
                    return {
                        **lesson,
                        "module_title": module["title"],  # Добавляем название модуля
                        "course_id": courses["course_id"]
                    }
        return None
    
    def get_lesson_topic(self, lesson_id: str) -> str:
        """Возвращает понятную тему для ИИ (не сырой ID)"""
        lesson = self.get_lesson(lesson_id)
        if lesson:
            return f"{lesson['module_title']}: {lesson['title']}"
        return lesson_id  # Фоллбэк
    
    def get_next_lesson_id(self, current_lesson_id: str) -> Optional[str]:
        """Находит ID следующего урока или None, если курс завершён"""
        courses = self._load_courses()
        found_module = False
        
        for module in courses.get("modules", []):
            lessons = module.get("lessons", [])
            
            # Ищем текущий урок в этом модуле
            for i, lesson in enumerate(lessons):
                if lesson["lesson_id"] == current_lesson_id:
                    # Есть ли следующий урок в этом модуле?
                    if i + 1 < len(lessons):
                        return lessons[i + 1]["lesson_id"]
                    # Иначе ищем первый урок следующего модуля
                    found_module = True
                    break
            
            # Если нашли текущий урок в этом модуле и он был последним
            if found_module:
                # Ищем следующий модуль
                module_idx = courses["modules"].index(module)
                if module_idx + 1 < len(courses["modules"]):
                    next_module = courses["modules"][module_idx + 1]
                    if next_module.get("lessons"):
                        return next_module["lessons"][0]["lesson_id"]
                return None  # Курс завершён
        
        return None  # Урок не найден