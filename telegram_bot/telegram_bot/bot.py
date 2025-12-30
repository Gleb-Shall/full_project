import os
import json
import logging
from typing import Dict, Any
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from gpt_client import GPTClient
from logo_analyzer import LogoAnalyzer
from json_manager import JSONManager
from api_client import APIClient

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения берутся из GitHub Secrets или системных переменных
# Для локальной разработки можно использовать .env файл через load_dotenv (опционально)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN не найден в переменных окружения")
        
        # Загружаем системные промпты
        self._load_prompts()
        
        self.gpt_client = GPTClient()
        self.logo_analyzer = LogoAnalyzer()
        self.json_manager = JSONManager()
        self.api_client = APIClient()
        
        # Состояния пользователей: {user_id: state}
        self.user_states: Dict[int, str] = {}
        # Данные пользователей: {user_id: {data}}
        self.user_data: Dict[int, Dict[str, Any]] = {}
        # История диалогов для GPT: {user_id: [messages]}
        self.conversation_history: Dict[int, list] = {}
        # Счетчик вопросов GPT: {user_id: count}
        self.gpt_question_count: Dict[int, int] = {}
        
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()
    
    def _load_prompts(self):
        """Загрузка системных промптов из файлов"""
        script_dir = Path(__file__).parent
        prompts_dir = script_dir / "prompts"
        
        # Загружаем промпт для генерации вопросов
        question_prompt_path = prompts_dir / "question_generation.txt"
        if question_prompt_path.exists():
            with open(question_prompt_path, 'r', encoding='utf-8') as f:
                self.question_generation_prompt = f.read()
        else:
            logger.warning(f"Промпт не найден: {question_prompt_path}, используем дефолтный")
            self.question_generation_prompt = """Ты помощник для сбора информации о бизнесе клиента для создания веб-сайта."""
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        # Команды обрабатываются первыми
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        # Обработчик кнопок (должен быть до других обработчиков)
        self.application.add_handler(CallbackQueryHandler(self.handle_button))
        # Затем фото
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        # И текстовые сообщения (не команды)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Инициализация данных пользователя
        self.user_states[user_id] = "waiting_business_name"
        self.user_data[user_id] = {
            "telegram_id": str(user_id),
            "name": username
        }
        self.conversation_history[user_id] = []
        self.gpt_question_count[user_id] = 0
        
        # Загружаем шаблон JSON
        self.json_manager.initialize_user_data(user_id)
        
        await update.message.reply_text(
            "👋 Привет! Я помогу вам создать конфигурацию для вашего сайта.\n\n"
            "Начнем с базовой информации.\n\n"
            "📝 Пожалуйста, укажите название вашего бизнеса:"
        )
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /reset - сброс данных"""
        user_id = update.effective_user.id
        self.user_states[user_id] = "waiting_business_name"
        self.user_data[user_id] = {}
        self.conversation_history[user_id] = []
        self.gpt_question_count[user_id] = 0
        self.json_manager.initialize_user_data(user_id)
        
        await update.message.reply_text(
            "🔄 Данные сброшены. Начнем заново!\n\n"
            "📝 Пожалуйста, укажите название вашего бизнеса:"
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик загрузки фото (логотипа или изображений для сайта)"""
        user_id = update.effective_user.id
        state = self.user_states.get(user_id)
        
        if state == "waiting_image":
            # Принимаем изображение для сайта
            await update.message.reply_text("📷 Изображение получено! Теперь укажите название для этого изображения:")
            
            try:
                # Скачиваем фото
                photo = update.message.photo[-1]  # Берем фото наибольшего размера
                file = await context.bot.get_file(photo.file_id)
                
                # Сохраняем информацию об изображении
                if "current_image" not in self.user_data[user_id]:
                    self.user_data[user_id]["current_image"] = {}
                
                # Формируем полный URL для файла
                full_url = f"https://api.telegram.org/file/bot{self.token}/{file.file_path}"
                
                # Сохраняем file_id и полный URL для дальнейшего использования
                self.user_data[user_id]["current_image"] = {
                    "file_id": photo.file_id,
                    "url": full_url,  # Полный URL файла в Telegram
                }
                
                # Переходим к запросу названия
                self.user_states[user_id] = "waiting_image_name"
                
            except Exception as e:
                logger.error(f"Ошибка при обработке изображения: {e}")
                await update.message.reply_text(
                    "❌ Произошла ошибка при обработке изображения. Попробуйте еще раз."
                )
        
        elif state == "waiting_logo":
            await update.message.reply_text("🖼️ Анализирую логотип...")
            
            try:
                # Скачиваем фото
                photo = update.message.photo[-1]  # Берем фото наибольшего размера
                file = await context.bot.get_file(photo.file_id)
                
                # Сохраняем временно
                script_dir = os.path.dirname(os.path.abspath(__file__))
                temp_path = os.path.join(script_dir, f"temp_logo_{user_id}.jpg")
                await file.download_to_drive(temp_path)
                
                # Анализируем логотип
                analysis = self.logo_analyzer.analyze_logo(temp_path)
                
                # Сохраняем результаты
                if "logo_analysis" not in self.user_data[user_id]:
                    self.user_data[user_id]["logo_analysis"] = {}
                
                self.user_data[user_id]["logo_analysis"] = analysis
                
                # Формируем полный URL для файла
                full_url = f"https://api.telegram.org/file/bot{self.token}/{file.file_path}"
                
                # Сохраняем информацию о логотипе в JSON
                logo_info = {
                    "file_id": photo.file_id,
                    "url": full_url,  # Полный URL файла в Telegram
                    "width": "200px"  # Можно настроить позже
                }
                self.json_manager.update_logo(user_id, logo_info)
                
                # Обновляем цвета дизайна на основе анализа
                self.json_manager.update_design_colors(user_id, analysis)
                
                # Удаляем временный файл
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                await update.message.reply_text(
                    f"✅ Логотип проанализирован!\n\n"
                    f"🎨 Основные цвета:\n"
                    f"{self._format_color_analysis(analysis)}\n\n"
                    f"Продолжаем сбор информации..."
                )
                
                # Обновляем информацию о наличии логотипа
                data = self.json_manager.get_user_json(user_id)
                if "design_wishes" not in data:
                    data["design_wishes"] = {}
                data["design_wishes"]["logo_available"] = True
                self.json_manager._save_user_json(user_id, data)
                
                # Переходим к GPT-вопросам
                self.user_states[user_id] = "gpt_questions"
                self.gpt_question_count[user_id] = 0
                if user_id not in self.conversation_history:
                    self.conversation_history[user_id] = []
                
                await update.message.reply_text(
                    "✅ Логотип сохранен!\n\n"
                    "🤖 Теперь я задам вам несколько вопросов, чтобы узнать ваши пожелания по сайту..."
                )
                
                # Генерируем первый вопрос через GPT
                await self._ask_gpt_question(update, context)
                
            except Exception as e:
                logger.error(f"Ошибка при анализе логотипа: {e}")
                await update.message.reply_text(
                    "❌ Произошла ошибка при анализе логотипа. "
                    "Попробуйте загрузить изображение еще раз."
                )
        else:
            await update.message.reply_text(
                "📷 Сейчас не ожидается загрузка изображения. "
                "Пожалуйста, следуйте инструкциям бота."
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user_id = update.effective_user.id
        text = update.message.text
        state = self.user_states.get(user_id, "waiting_business_name")
        
        if state == "waiting_business_name":
            # Сохраняем название бизнеса
            self.json_manager.update_business_name(user_id, text)
            self.user_data[user_id]["business_name"] = text
            
            # Переходим к вопросу о логотипе
            self.user_states[user_id] = "waiting_logo"
            await update.message.reply_text(
                f"✅ Название бизнеса сохранено: {text}\n\n"
                "🖼️ Есть ли у вас логотип? Если да, отправьте его фото. "
                "Если нет, отправьте 'нет' или 'skip'."
            )
        
        elif state == "waiting_logo":
            # Пользователь ответил текстом вместо фото
            if text.lower() in ['нет', 'no', 'skip', 'пропустить']:
                # Обновляем информацию о наличии логотипа
                data = self.json_manager.get_user_json(user_id)
                if "design_wishes" not in data:
                    data["design_wishes"] = {}
                data["design_wishes"]["logo_available"] = False
                self.json_manager._save_user_json(user_id, data)
                
                # Переходим к GPT-вопросам
                self.user_states[user_id] = "gpt_questions"
                self.gpt_question_count[user_id] = 0
                if user_id not in self.conversation_history:
                    self.conversation_history[user_id] = []
                
                await update.message.reply_text(
                    "✅ Понятно. Переходим к следующим вопросам...\n\n"
                    "🤖 Теперь я задам вам несколько вопросов, чтобы узнать ваши пожелания по сайту..."
                )
                
                # Генерируем первый вопрос через GPT
                await self._ask_gpt_question(update, context)
            else:
                await update.message.reply_text(
                    "Пожалуйста, отправьте фото логотипа или напишите 'нет' для пропуска."
                )
        elif state == "waiting_industry":
            # Сохраняем сферу работы в новую структуру
            data = self.json_manager.get_user_json(user_id)
            if "project" not in data:
                data["project"] = {}
            if "business" not in data["project"]:
                data["project"]["business"] = {}
            data["project"]["business"]["industry"] = text
            self.json_manager._save_user_json(user_id, data)
            
            # Переходим к GPT-вопросам
            self.user_states[user_id] = "gpt_questions"
            self.gpt_question_count[user_id] = 0
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            await update.message.reply_text(
                "✅ Понятно. Переходим к следующим вопросам...\n\n"
                "🤖 Теперь я задам вам несколько вопросов, чтобы узнать ваши пожелания по сайту..."
            )
            
            # Генерируем первый вопрос через GPT
            await self._ask_gpt_question(update, context)
        
        elif state == "waiting_image_name":
            # Сохраняем название изображения
            image_data = self.user_data[user_id].get("current_image", {})
            if image_data:
                image_data["name"] = text
                image_data["alt"] = text  # Используем название как alt текст
                
                # Добавляем изображение в JSON
                self.json_manager.add_image_to_gallery(user_id, image_data)
                
                await update.message.reply_text(
                    f"✅ Изображение сохранено: {text}\n\n"
                    "Отправьте следующее изображение или напишите 'готово' / 'завершить' для продолжения."
                )
                
                # Очищаем текущее изображение
                self.user_data[user_id]["current_image"] = {}
                self.user_states[user_id] = "waiting_image"
        
        elif state == "waiting_image":
            # Пользователь написал текст вместо отправки изображения
            if text.lower() in ['готово', 'завершить', 'done', 'finish', 'далее', 'продолжить']:
                # Переходим к GPT-вопросам
                self.user_states[user_id] = "gpt_questions"
                self.gpt_question_count[user_id] = 0
                await update.message.reply_text(
                    "✅ Переходим к следующим вопросам...\n\n"
                    "🤖 Теперь я задам вам несколько вопросов для уточнения деталей..."
                )
                
                # Генерируем первый вопрос через GPT
                await self._ask_gpt_question(update, context)
            else:
                await update.message.reply_text(
                    "Пожалуйста, отправьте изображение или напишите 'готово' для продолжения."
                )
        
        elif state == "gpt_questions":
            # Сохраняем ответ пользователя в историю
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            self.conversation_history[user_id].append({
                "role": "user",
                "content": text
            })
            
            # Сохраняем переписку в JSON
            data = self.json_manager.get_user_json(user_id)
            if "context" not in data:
                data["context"] = {}
            data["context"]["conversation"] = self.conversation_history[user_id].copy()
            self.json_manager._save_user_json(user_id, data)
            
            # Обновляем JSON на основе ответа
            await self._process_user_answer(user_id, text)
            
            # Проверяем, не слишком ли много вопросов задано
            question_count = self.gpt_question_count.get(user_id, 0)
            if question_count >= 10:
                # Если задано 10+ вопросов, завершаем сбор
                await self._finish_data_collection(update, context)
            else:
                # Генерируем следующий вопрос
                await self._ask_gpt_question(update, context)
    
    async def _ask_gpt_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Генерация вопроса через GPT на основе текущего состояния"""
        user_id = update.effective_user.id
        
        try:
            # Инициализируем conversation_history если его нет
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            # Получаем текущее состояние JSON
            current_json = self.json_manager.get_user_json(user_id)
            
            # Формируем системный промпт
            system_prompt = self._create_system_prompt(current_json)
            
            # Генерируем вопрос
            question = await self.gpt_client.generate_question(
                system_prompt=system_prompt,
                conversation_history=self.conversation_history[user_id]
            )
            
            if question:
                # Добавляем вопрос в историю
                self.conversation_history[user_id].append({
                    "role": "assistant",
                    "content": question
                })
                
                # Сохраняем переписку в JSON
                data = self.json_manager.get_user_json(user_id)
                if "context" not in data:
                    data["context"] = {}
                data["context"]["conversation"] = self.conversation_history[user_id].copy()
                self.json_manager._save_user_json(user_id, data)
                
                # Увеличиваем счетчик вопросов
                self.gpt_question_count[user_id] = self.gpt_question_count.get(user_id, 0) + 1
                
                # Отправляем вопрос через context.bot если update.message недоступен
                if update.message:
                    await update.message.reply_text(question)
                elif update.callback_query and update.callback_query.message:
                    await context.bot.send_message(
                        chat_id=update.callback_query.message.chat_id,
                        text=question
                    )
            else:
                # Если вопросов больше нет, завершаем сбор данных
                await self._finish_data_collection(update, context)
        
        except Exception as e:
            logger.error(f"Ошибка при генерации вопроса: {e}", exc_info=True)
            # Отправляем сообщение об ошибке
            try:
                if update.message:
                    await update.message.reply_text(
                        "❌ Произошла ошибка. Попробуйте еще раз или используйте /reset для начала заново."
                    )
                elif update.callback_query and update.callback_query.message:
                    await context.bot.send_message(
                        chat_id=update.callback_query.message.chat_id,
                        text="❌ Произошла ошибка. Попробуйте еще раз или используйте /reset для начала заново."
                    )
            except Exception as send_error:
                logger.error(f"Ошибка при отправке сообщения об ошибке: {send_error}")
    
    async def _process_user_answer(self, user_id: int, answer: str):
        """Обработка ответа пользователя и обновление JSON"""
        try:
            # Используем GPT для извлечения структурированных данных из ответа
            current_json = self.json_manager.get_user_json(user_id)
            
            extracted_data = await self.gpt_client.extract_data_from_answer(
                answer=answer,
                current_json=current_json,
                conversation_history=self.conversation_history[user_id]
            )
            
            # Обновляем JSON
            if extracted_data:
                self.json_manager.update_from_extracted_data(user_id, extracted_data)
        
        except Exception as e:
            logger.error(f"Ошибка при обработке ответа: {e}")
    
    async def _finish_data_collection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершение сбора данных и отправка JSON"""
        user_id = update.effective_user.id
        
        try:
            # Обновляем Telegram ID в JSON
            self.json_manager.update_telegram_id(user_id, str(user_id))
            
            # Сохраняем переписку в context
            if user_id in self.conversation_history:
                data = self.json_manager.get_user_json(user_id)
                if "context" not in data:
                    data["context"] = {}
                data["context"]["conversation"] = self.conversation_history[user_id]
                self.json_manager._save_user_json(user_id, data)
            
            # Финальное обновление JSON
            self.json_manager.finalize_json(user_id)
            
            # Получаем финальный JSON
            final_json = self.json_manager.get_user_json(user_id)
            
            await update.message.reply_text(
                "✅ Сбор информации завершен! Отправляю данные на генерацию сайта...\n\n"
                "⏳ Это может занять несколько минут. Пожалуйста, подождите..."
            )
            
            # Отправляем JSON на эндпоинт
            result = await self.api_client.send_json(final_json, user_id)
            
            if result.get("success"):
                url = result.get("url")
                if url:
                    await update.message.reply_text(
                        "🎉 Отлично! Ваш сайт успешно создан и задеплоен!\n\n"
                        f"🌐 Ссылка на сайт: {url}\n\n"
                        "Спасибо за использование бота! 🎉\n\n"
                        "Используйте /start для создания нового сайта."
                    )
                else:
                    # Сайт сгенерирован, но деплой не удался
                    await update.message.reply_text(
                        "✅ Сайт успешно сгенерирован!\n\n"
                        "⚠️ Однако произошла ошибка при деплое. "
                        "Пожалуйста, свяжитесь с администратором.\n\n"
                        "Используйте /start для нового проекта."
                    )
            else:
                error_message = result.get("message", "Unknown error")
                await update.message.reply_text(
                    f"❌ Произошла ошибка при генерации сайта.\n\n"
                    f"Ошибка: {error_message}\n\n"
                    "Пожалуйста, попробуйте еще раз или свяжитесь с администратором.\n\n"
                    "Используйте /start для нового проекта."
                )
            
            # Сбрасываем состояние
            self.user_states[user_id] = "completed"
        
        except Exception as e:
            logger.error(f"Ошибка при завершении сбора данных: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка: {str(e)}\n\n"
                "Попробуйте использовать /reset для начала заново."
            )
    
    def _create_system_prompt(self, current_json: Dict[str, Any]) -> str:
        """Создание системного промпта для GPT"""
        filled_fields = self._get_filled_fields_summary(current_json)
        missing_fields = self._get_missing_fields(current_json)
        
        # Форматируем промпт с заполненными данными
        return self.question_generation_prompt.format(
            filled_fields=filled_fields,
            missing_fields=missing_fields
        )

    def _get_filled_fields_summary(self, json_data: Dict[str, Any]) -> str:
        """Получение краткого описания заполненных полей"""
        summary = []
        project = json_data.get("project", {})
        business = project.get("business", {})
        goals = json_data.get("goals", {})
        content_wishes = json_data.get("content_wishes", {})
        design_wishes = json_data.get("design_wishes", {})
        
        if business.get("name"):
            summary.append(f"Название бизнеса: {business['name']}")
        
        if business.get("industry"):
            summary.append(f"Сфера: {business['industry']}")
        
        if business.get("description"):
            summary.append(f"Описание бизнеса: {business['description']}")
        
        if business.get("unique_selling_proposition"):
            summary.append(f"УТП: {business['unique_selling_proposition']}")
        
        if goals.get("main_goal"):
            summary.append(f"Главная цель: {goals['main_goal']}")
        
        target_audience = goals.get("target_audience", {})
        if target_audience.get("age_range") or target_audience.get("gender"):
            aud = []
            if target_audience.get("age_range"):
                aud.append(f"возраст: {target_audience['age_range']}")
            if target_audience.get("gender"):
                aud.append(f"пол: {target_audience['gender']}")
            if target_audience.get("geography"):
                aud.append(f"география: {target_audience['geography']}")
            if aud:
                summary.append(f"Целевая аудитория: {', '.join(aud)}")
        
        if content_wishes.get("services_or_products"):
            summary.append(f"Услуги/товары: {', '.join(content_wishes['services_or_products'])}")
        
        if design_wishes.get("logo_available") is not None:
            summary.append(f"Логотип: {'есть' if design_wishes['logo_available'] else 'нет'}")
        
        return "\n".join(summary) if summary else "Пока ничего не заполнено"
    
    def _get_missing_fields(self, json_data: Dict[str, Any]) -> str:
        """Получение списка важных незаполненных полей"""
        missing = []
        project = json_data.get("project", {})
        business = project.get("business", {})
        goals = json_data.get("goals", {})
        content_wishes = json_data.get("content_wishes", {})
        design_wishes = json_data.get("design_wishes", {})
        functionality_wishes = json_data.get("functionality_wishes", {})
        
        if not goals.get("main_goal"):
            missing.append("- Главная цель сайта (для чего он нужен)")
        
        target_audience = goals.get("target_audience", {})
        if not target_audience.get("age_range") and not target_audience.get("gender"):
            missing.append("- Целевая аудитория (кто ваши клиенты)")
        
        if not business.get("description"):
            missing.append("- Описание бизнеса (чем вы занимаетесь)")
        
        if not business.get("unique_selling_proposition"):
            missing.append("- Уникальное торговое предложение (чем вы отличаетесь)")
        
        if not content_wishes.get("services_or_products"):
            missing.append("- Что показать на сайте (услуги, товары, что важно)")
        
        if not content_wishes.get("what_to_tell"):
            missing.append("- Что рассказать о себе/компании")
        
        if design_wishes.get("logo_available") is None:
            missing.append("- Наличие логотипа")
        
        if not functionality_wishes.get("contact_form") and not functionality_wishes.get("online_booking"):
            missing.append("- Функциональность (форма обратной связи, онлайн-запись и т.д.)")
        
        references = json_data.get("references", {})
        if not references.get("liked_websites"):
            missing.append("- Референсы (примеры сайтов, которые нравятся)")
        
        return "\n".join(missing) if missing else "Все важные поля заполнены"
    
    async def _ask_about_images(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запрос о наличии изображений для сайта"""
        keyboard = [
            [
                InlineKeyboardButton("Да", callback_data="images_yes"),
                InlineKeyboardButton("Нет", callback_data="images_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🖼️ У вас есть изображения, которые вы бы хотели добавить на сайт?",
            reply_markup=reply_markup
        )
    
    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        try:
            query = update.callback_query
            
            if not query:
                logger.error("Callback query is None")
                return
            
            await query.answer()
            
            user_id = query.from_user.id
            data = query.data
            
            logger.info(f"Обработка кнопки: {data} для пользователя {user_id}")
            
            if data == "images_yes":
                self.user_states[user_id] = "waiting_image"
                # Инициализируем список изображений
                if user_id not in self.user_data:
                    self.user_data[user_id] = {}
                if "images" not in self.user_data[user_id]:
                    self.user_data[user_id]["images"] = []
                
                await query.edit_message_text(
                    "📷 Отлично! Отправляйте изображения по одному.\n\n"
                    "После каждого изображения укажите его название.\n"
                    "Когда закончите, напишите 'готово' или 'завершить'."
                )
            
            elif data == "images_no":
                # Переходим к GPT-вопросам
                self.user_states[user_id] = "gpt_questions"
                self.gpt_question_count[user_id] = 0
                
                # Инициализируем conversation_history если его нет
                if user_id not in self.conversation_history:
                    self.conversation_history[user_id] = []
                
                await query.edit_message_text(
                    "✅ Понятно. Переходим к следующим вопросам...\n\n"
                    "🤖 Теперь я задам вам несколько вопросов для уточнения деталей..."
                )
                
                # Генерируем первый вопрос через GPT
                # Используем query.message для создания update
                fake_message = query.message
                fake_update = Update(update_id=update.update_id, message=fake_message)
                await self._ask_gpt_question(fake_update, context)
            else:
                logger.warning(f"Неизвестный callback_data: {data}")
                await query.answer("Неизвестная команда", show_alert=True)
        
        except Exception as e:
            logger.error(f"Ошибка при обработке кнопки: {e}", exc_info=True)
            if query:
                try:
                    await query.answer("Произошла ошибка. Попробуйте еще раз.", show_alert=True)
                except:
                    pass
    
    def _format_color_analysis(self, analysis: Dict[str, Any]) -> str:
        """Форматирование результатов анализа цветов"""
        colors = analysis.get("colors", [])
        outline_color = analysis.get("outline_color", "")
        
        result = []
        for i, color_info in enumerate(colors[:5], 1):  # Показываем топ-5 цветов
            color = color_info.get("color", "")
            percentage = color_info.get("percentage", 0)
            result.append(f"{i}. {color} ({percentage:.1f}%)")
        
        if outline_color:
            result.append(f"\nКонтур: {outline_color}")
        
        return "\n".join(result) if result else "Цвета не обнаружены"
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск Telegram бота...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()

