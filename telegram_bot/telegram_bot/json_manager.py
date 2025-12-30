import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class JSONManager:
    def __init__(self):
        # Определяем путь к шаблону относительно корня проекта
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        self.base_template_path = os.path.join(project_root, "chat", "output.json")
        self.user_data_dir = os.path.join(script_dir, "user_data")
        
        # Создаем директорию для данных пользователей
        os.makedirs(self.user_data_dir, exist_ok=True)
    
    def _get_user_json_path(self, user_id: int) -> str:
        """Получение пути к JSON файлу пользователя"""
        return os.path.join(self.user_data_dir, f"user_{user_id}.json")
    
    def _load_template(self) -> Dict[str, Any]:
        """Загрузка шаблона JSON"""
        try:
            with open(self.base_template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке шаблона: {e}")
            return self._get_empty_template()
    
    def _get_empty_template(self) -> Dict[str, Any]:
        """Создание пустого шаблона если файл не найден"""
        return {
            "project": {
                "client": {
                    "name": "",
                    "phone": "",
                    "email": "",
                    "telegram id": "",
                    "telegram username": "",
                    "preferred_contact": "telegram"
                },
                "business": {
                    "name": "",
                    "industry": "",
                    "location": "",
                    "description": "",
                    "unique_selling_proposition": "",
                    "competitors": "",
                    "advantages": []
                }
            },
            "goals": {
                "main_goal": "",
                "target_audience": {
                    "age_range": "",
                    "gender": "",
                    "interests": "",
                    "geography": "",
                    "pain_points": "",
                    "needs": ""
                },
                "expected_results": "",
                "success_metrics": "",
                "call_to_action": ""
            },
            "content_wishes": {
                "what_to_show": [],
                "what_to_tell": [],
                "key_messages": [],
                "services_or_products": [],
                "prices_visibility": False,
                "testimonials_available": False,
                "portfolio_available": False,
                "about_company": "",
                "contact_preferences": ""
            },
            "structure_wishes": {
                "must_have_sections": [],
                "nice_to_have_sections": [],
                "content_priority": [],
                "user_journey": "",
                "important_information": []
            },
            "design_wishes": {
                "style_preferences": "",
                "color_preferences": "",
                "mood": "",
                "references": [],
                "liked_examples": [],
                "disliked_examples": [],
                "brand_guidelines": "",
                "logo_available": False
            },
            "functionality_wishes": {
                "contact_form": False,
                "online_booking": False,
                "payment_integration": False,
                "social_media_integration": False,
                "chat_widget": False,
                "map": False,
                "video": False,
                "gallery": False,
                "calculator": False,
                "other_features": []
            },
            "content_assets": {
                "texts_ready": False,
                "images_ready": False,
                "videos_ready": False,
                "who_provides_content": "",
                "content_help_needed": False,
                "available_materials": []
            },
            "references": {
                "liked_websites": [],
                "liked_designs": [],
                "competitor_sites": [],
                "inspiration_sources": []
            },
            "technical_wishes": {
                "mobile_priority": False,
                "loading_speed": "",
                "seo_important": False,
                "analytics_needed": False,
                "cms_preference": "",
                "integration_needs": []
            },
            "additional_wishes": {
                "budget_range": "",
                "timeline": "",
                "special_requirements": [],
                "concerns": [],
                "questions": [],
                "other_notes": ""
            },
            "generated_structure": {
                "sections": [],
                "navigation": [],
                "footer": {}
            },
            "generated_design": {
                "style": "",
                "colors": {
                    "primary": "",
                    "secondary": "",
                    "accent": "",
                    "background": "",
                    "text": ""
                },
                "fonts": {
                    "heading": "",
                    "body": ""
                }
            },
            "generated_content": {
                "hero": {
                    "headline": "",
                    "subheadline": "",
                    "cta_text": ""
                },
                "sections": []
            },
            "images": {
                "logo": {
                    "url": "",
                    "file_id": "",
                    "width": "200px"
                },
                "gallery": []
            },
            "context": {
                "conversation": []
            },
            "timeline": {
                "status": "draft",
                "generated_at": "",
                "deployed_at": "",
                "notes": ""
            }
        }
    
    def initialize_user_data(self, user_id: int):
        """Инициализация данных пользователя из шаблона"""
        template = self._load_template()
        self._save_user_json(user_id, template)
    
    def get_user_json(self, user_id: int) -> Dict[str, Any]:
        """Получение JSON данных пользователя"""
        json_path = self._get_user_json_path(user_id)
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка при загрузке JSON пользователя {user_id}: {e}")
                return self._load_template()
        else:
            return self._load_template()
    
    def _save_user_json(self, user_id: int, data: Dict[str, Any]):
        """Сохранение JSON данных пользователя"""
        json_path = self._get_user_json_path(user_id)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении JSON пользователя {user_id}: {e}")
    
    def update_business_name(self, user_id: int, name: str):
        """Обновление названия бизнеса"""
        data = self.get_user_json(user_id)
        data["project"]["business"]["name"] = name
        self._save_user_json(user_id, data)
    
    def update_industry(self, user_id: int, industry: str):
        """Обновление сферы работы"""
        data = self.get_user_json(user_id)
        data["project"]["business"]["industry"] = industry
        self._save_user_json(user_id, data)
    
    def update_logo(self, user_id: int, logo_info: Dict[str, Any]):
        """Обновление информации о логотипе в JSON"""
        data = self.get_user_json(user_id)
        
        # Обновляем информацию о логотипе
        if "logo" not in data.get("design", {}).get("images", {}):
            data["design"]["images"]["logo"] = {}
        
        data["design"]["images"]["logo"]["url"] = logo_info.get("url", "")
        data["design"]["images"]["logo"]["file_id"] = logo_info.get("file_id", "")
        if "width" in logo_info:
            data["design"]["images"]["logo"]["width"] = logo_info.get("width", "200px")
        
        self._save_user_json(user_id, data)
    
    def update_design_colors(self, user_id: int, logo_analysis: Dict[str, Any]):
        """Обновление цветов дизайна на основе анализа логотипа"""
        data = self.get_user_json(user_id)
        colors = logo_analysis.get("colors", [])
        outline_color = logo_analysis.get("outline_color", "")
        
        if colors:
            # Используем первый цвет как primary
            if len(colors) > 0:
                data["design"]["colors"]["primary"] = colors[0].get("color", "#3b82f6")
            
            # Второй цвет как secondary
            if len(colors) > 1:
                data["design"]["colors"]["secondary"] = colors[1].get("color", "#10b981")
            
            # Третий цвет как accent
            if len(colors) > 2:
                data["design"]["colors"]["accent"] = colors[2].get("color", "#f59e0b")
            
            # Остальные цвета в custom
            custom_colors = [c.get("color") for c in colors[3:]]
            data["design"]["colors"]["custom"] = custom_colors
        
        if outline_color:
            # Можно использовать цвет контура для текста или другого элемента
            data["design"]["colors"]["text"] = outline_color
        
        self._save_user_json(user_id, data)
    
    def update_from_extracted_data(self, user_id: int, extracted_data: Dict[str, Any]):
        """Обновление JSON из извлеченных GPT данных"""
        data = self.get_user_json(user_id)
        
        # Рекурсивное обновление
        self._deep_update(data, extracted_data)
        
        self._save_user_json(user_id, data)
    
    def _deep_update(self, base: Dict[str, Any], update: Dict[str, Any]):
        """Рекурсивное обновление словаря"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                if value:  # Обновляем только если значение не пустое
                    base[key] = value
    
    def update_telegram_id(self, user_id: int, telegram_id: str):
        """Обновление Telegram ID клиента"""
        data = self.get_user_json(user_id)
        data["project"]["client"]["telegram id"] = telegram_id
        self._save_user_json(user_id, data)
    
    def add_image_to_gallery(self, user_id: int, image_data: Dict[str, Any]):
        """Добавление изображения в галерею"""
        data = self.get_user_json(user_id)
        
        # Инициализируем gallery если его нет
        if "gallery" not in data.get("design", {}).get("images", {}):
            data["design"]["images"]["gallery"] = []
        
        # Добавляем изображение в галерею
        gallery_item = {
            "url": image_data.get("url", ""),
            "file_id": image_data.get("file_id", ""),
            "name": image_data.get("name", ""),
            "alt": image_data.get("alt", image_data.get("name", ""))
        }
        
        data["design"]["images"]["gallery"].append(gallery_item)
        self._save_user_json(user_id, data)
    
    def finalize_json(self, user_id: int):
        """Финальное обновление JSON перед отправкой и преобразование в формат генератора"""
        data = self.get_user_json(user_id)
        
        # Обновляем timeline
        if "timeline" not in data:
            data["timeline"] = {}
        data["timeline"]["status"] = "ready"
        data["timeline"]["generated_at"] = datetime.now().isoformat()
        
        # Преобразуем структуру бота в структуру генератора
        # Создаем поле design, если его нет
        if "design" not in data:
            data["design"] = {}
        
        # Заполняем design из generated_design или design_wishes
        if "generated_design" in data:
            gen_design = data["generated_design"]
            if "style" in gen_design and gen_design["style"]:
                data["design"]["style"] = gen_design["style"]
            if "colors" in gen_design:
                data["design"]["colors"] = gen_design["colors"]
            if "fonts" in gen_design:
                data["design"]["fonts"] = gen_design["fonts"]
        
        # Если colors нет, создаем дефолтные
        if "colors" not in data["design"]:
            data["design"]["colors"] = {}
        
        # Заполняем дефолтными значениями, если они пустые
        default_colors = {
            "primary": "#3b82f6",
            "secondary": "#10b981",
            "accent": "#f59e0b",
            "background": "#ffffff",
            "text": "#1f2937",
            "custom": []
        }
        
        for key, default_value in default_colors.items():
            if key not in data["design"]["colors"] or not data["design"]["colors"][key]:
                data["design"]["colors"][key] = default_value
        
        # Если fonts нет, создаем дефолтные
        if "fonts" not in data["design"]:
            data["design"]["fonts"] = {
                "heading": "Inter",
                "body": "Inter",
                "sizes": {
                    "h1": "3rem",
                    "h2": "2.5rem",
                    "h3": "2rem",
                    "body": "1rem"
                }
            }
        
        # Создаем images в design, если его нет
        if "images" not in data["design"]:
            data["design"]["images"] = {
                "hero": {"url": "", "alt": "", "position": "center"},
                "features": [],
                "about": {"url": "", "alt": ""},
                "gallery": [],
                "logo": {"url": "", "width": "200px"}
            }
        
        # Копируем logo из images если есть
        if "images" in data and "logo" in data["images"]:
            logo = data["images"]["logo"]
            if logo.get("url"):
                data["design"]["images"]["logo"]["url"] = logo["url"]
            if logo.get("width"):
                data["design"]["images"]["logo"]["width"] = logo["width"]
        
        # Создаем content, если его нет
        if "content" not in data:
            data["content"] = {
                "language": "ru",
                "hero": {"headline": "", "subheadline": "", "cta_text": "Связаться", "cta_url": "#contacts"},
                "sections": [],
                "features": [],
                "services": [],
                "testimonials": [],
                "contacts": {}
            }
        
        # Заполняем content из generated_content
        if "generated_content" in data:
            gen_content = data["generated_content"]
            if "hero" in gen_content:
                data["content"]["hero"].update(gen_content["hero"])
            if "sections" in gen_content:
                data["content"]["sections"] = gen_content["sections"]
        
        # Создаем structure, если его нет
        if "structure" not in data:
            data["structure"] = {
                "pages": [{"path": "index", "title": "Главная", "sections": []}],
                "navigation": [{"title": "Главная", "url": "/", "visible": True}],
                "footer": {"links": [], "social": {}, "copyright": ""}
            }
        
        # Заполняем structure из generated_structure
        if "generated_structure" in data:
            gen_struct = data["generated_structure"]
            if "sections" in gen_struct:
                data["structure"]["pages"][0]["sections"] = gen_struct["sections"]
            if "navigation" in gen_struct:
                data["structure"]["navigation"] = gen_struct["navigation"]
            if "footer" in gen_struct:
                data["structure"]["footer"].update(gen_struct["footer"])
        
        # Обновляем copyright в structure.footer
        business_name = data.get("project", {}).get("business", {}).get("name", "Компания")
        if "footer" in data["structure"] and isinstance(data["structure"]["footer"], dict):
            data["structure"]["footer"]["copyright"] = f"© {datetime.now().year} {business_name}"
        
        # Создаем technical, если его нет
        if "technical" not in data:
            data["technical"] = {
                "domain": "",
                "seo": {"title": "", "description": "", "keywords": [], "opengraph": {}},
                "analytics": {},
                "features": {"forms": False, "animations": "subtle", "responsive": True, "pwa": False}
            }
        
        self._save_user_json(user_id, data)

