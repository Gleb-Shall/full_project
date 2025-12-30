import os
import aiohttp
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class GPTClient:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "openai/gpt-4o-mini"
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY не найден в переменных окружения")
        
        # Загружаем промпт для извлечения данных
        self._load_data_extraction_prompt()
    
    def _load_data_extraction_prompt(self):
        """Загрузка промпта для извлечения данных из файла"""
        script_dir = Path(__file__).parent
        prompts_dir = script_dir / "prompts"
        
        data_extraction_prompt_path = prompts_dir / "data_extraction.txt"
        if data_extraction_prompt_path.exists():
            with open(data_extraction_prompt_path, 'r', encoding='utf-8') as f:
                self.data_extraction_prompt_template = f.read()
        else:
            logger.warning(f"Промпт не найден: {data_extraction_prompt_path}, используем дефолтный")
            self.data_extraction_prompt_template = """Ты помощник для извлечения структурированных данных из ответов пользователя."""
    
    async def generate_question(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]]
    ) -> Optional[str]:
        """Генерация вопроса на основе системного промпта и истории диалога"""
        try:
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Добавляем историю диалога
            messages.extend(conversation_history)
            
            # Если история пуста, добавляем начальный контекст
            if not conversation_history:
                messages.append({
                    "role": "user",
                    "content": "Начни задавать вопросы для заполнения информации о бизнесе."
                })
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/automatorio/telegram-bot",
                    "X-Title": "Automatorio Telegram Bot"
                }
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7
                    # Не устанавливаем max_tokens - используем ограничение в промпте (300 слов)
                }
                
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # Проверяем, завершен ли сбор данных
                        if "DATA_COLLECTION_COMPLETE" in content.upper():
                            return None
                        
                        return content.strip()
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка API OpenRouter: {response.status} - {error_text}")
                        return None
        
        except Exception as e:
            logger.error(f"Ошибка при генерации вопроса: {e}")
            return None
    
    async def extract_data_from_answer(
        self,
        answer: str,
        current_json: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """Извлечение структурированных данных из ответа пользователя"""
        try:
            # Форматируем промпт с текущим JSON
            system_prompt = self.data_extraction_prompt_template.format(
                current_json=json.dumps(current_json, ensure_ascii=False, indent=2)
            )

            messages = [
                {"role": "system", "content": system_prompt},
                *conversation_history[-3:],  # Берем последние 3 сообщения для контекста
                {"role": "user", "content": f"Извлеки данные из этого ответа: {answer}"}
            ]
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/automatorio/telegram-bot",
                    "X-Title": "Automatorio Telegram Bot"
                }
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"}
                }
                
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        try:
                            # Очищаем контент от возможных markdown блоков и лишних символов
                            content = content.strip()
                            
                            # Удаляем markdown блоки кода если есть
                            if content.startswith("```"):
                                # Находим первую и последнюю ```
                                first_backtick = content.find("```")
                                if first_backtick != -1:
                                    # Пропускаем ``` и возможный язык (json, etc)
                                    start = content.find("\n", first_backtick) + 1
                                    last_backtick = content.rfind("```")
                                    if last_backtick != -1:
                                        content = content[start:last_backtick].strip()
                            
                            # Пробуем распарсить JSON
                            extracted = json.loads(content)
                            return extracted
                        except json.JSONDecodeError as e:
                            logger.error(f"Не удалось распарсить JSON из ответа GPT: {e}")
                            logger.error(f"Содержимое ответа: {content[:500]}")  # Логируем первые 500 символов
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка API OpenRouter при извлечении данных: {response.status} - {error_text}")
                        return None
        
        except Exception as e:
            logger.error(f"Ошибка при извлечении данных: {e}")
            return None

