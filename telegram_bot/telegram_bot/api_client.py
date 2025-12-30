import os
import aiohttp
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        # Используем SITE_GENERATOR_API_URL из GitHub Secrets
        # Fallback на старый API_ENDPOINT для обратной совместимости
        self.endpoint = os.getenv('SITE_GENERATOR_API_URL') or os.getenv('API_ENDPOINT', 'http://localhost:3000/api/submit')
        self.timeout = 30
    
    async def send_json(self, json_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """
        Отправка JSON данных на эндпоинт и получение ответа с URL
        
        Returns:
            Dict с ключами:
            - success: bool - успешность операции
            - url: str | None - URL задеплоенного сайта (если успешно)
            - message: str - сообщение об ошибке или статусе
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "user_id": user_id,
                    "data": json_data
                }
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=600)  # 10 минут на генерацию и деплой
                ) as response:
                    if response.status in [200, 201]:
                        # Получаем ответ с URL
                        result = await response.json()
                        url = result.get('url')
                        message = result.get('message', 'Site generated and deployed successfully')
                        
                        logger.info(f"JSON успешно отправлен для пользователя {user_id}, URL: {url}")
                        return {
                            "success": True,
                            "url": url,
                            "message": message
                        }
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Ошибка при отправке JSON: {response.status} - {error_text}"
                        )
                        return {
                            "success": False,
                            "url": None,
                            "message": f"API error: {response.status}"
                        }
        
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при отправке JSON: {e}")
            return {
                "success": False,
                "url": None,
                "message": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке JSON: {e}")
            return {
                "success": False,
                "url": None,
                "message": f"Unexpected error: {str(e)}"
            }

