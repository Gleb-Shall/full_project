"""
API endpoint для генератора сайтов
Принимает JSON от Telegram бота, генерирует сайт и отправляет на Deploy API
"""
import os
import json
import logging
import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
from main import generate_site

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Site Generator API", version="1.0.0")

# CORS middleware для работы с Telegram ботом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    """Модель запроса на генерацию сайта"""
    user_id: Optional[int] = None
    data: Dict[str, Any]


class GenerateResponse(BaseModel):
    """Модель ответа после генерации"""
    success: bool
    message: str
    url: Optional[str] = None
    telegram_id: Optional[str] = None


async def send_to_deploy_api(files_data: Dict[str, Any], telegram_id: str) -> Optional[str]:
    """
    Отправляет сгенерированные файлы на Deploy API
    
    Args:
        files_data: Словарь с ключом "files", содержащий список файлов
        telegram_id: Telegram ID клиента
        
    Returns:
        URL задеплоенного сайта или None при ошибке
    """
    deploy_api_url = os.getenv('DEPLOY_API_URL', 'http://deploy-api:8000')
    endpoint = f"{deploy_api_url}/deploy"
    
    try:
        # Формируем данные для отправки
        # Deploy API ожидает файл с JSON структурой
        # Конвертируем files_data в JSON строку для отправки как файл
        import io
        
        # Создаем JSON файл в памяти
        json_content = json.dumps(files_data, ensure_ascii=False, indent=2)
        json_file = io.BytesIO(json_content.encode('utf-8'))
        
        # Отправляем multipart/form-data запрос
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field('file', 
                              json_file, 
                              filename='site.json',
                              content_type='application/json')
            
            async with session.post(
                endpoint,
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 минут на деплой
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    deployed_url = result.get('url')
                    logger.info(f"Site deployed successfully: {deployed_url}")
                    return deployed_url
                else:
                    error_text = await response.text()
                    logger.error(f"Deploy API error: {response.status} - {error_text}")
                    return None
                    
    except aiohttp.ClientError as e:
        logger.error(f"Network error sending to Deploy API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending to Deploy API: {e}")
        return None


@app.post("/generator", response_model=GenerateResponse)
@app.post("/api/submit", response_model=GenerateResponse)  # Для обратной совместимости
async def generate_and_deploy(request: GenerateRequest):
    """
    Генерирует сайт из JSON данных и отправляет на деплой
    
    Args:
        request: Запрос с данными для генерации сайта
        
    Returns:
        Ответ с URL задеплоенного сайта
    """
    try:
        logger.info(f"Received generation request for user_id: {request.user_id}")
        
        # Генерируем сайт
        logger.info("Starting site generation...")
        result = generate_site(request.data)
        
        if not result or 'files' not in result:
            raise HTTPException(
                status_code=500,
                detail="Site generation failed - no files generated"
            )
        
        logger.info(f"Site generated successfully: {len(result['files'])} files")
        
        # Извлекаем telegram_id из результата
        telegram_id = None
        for file_item in result['files']:
            if isinstance(file_item, dict) and 'telegram id' in file_item:
                telegram_id = file_item.get('telegram id', '')
                break
        
        # Если telegram_id не найден, используем из запроса
        if not telegram_id and request.user_id:
            telegram_id = str(request.user_id)
        
        # Отправляем на Deploy API
        logger.info("Sending to Deploy API...")
        deployed_url = await send_to_deploy_api(result, telegram_id or "")
        
        if deployed_url:
            return GenerateResponse(
                success=True,
                message="Site generated and deployed successfully",
                url=deployed_url,
                telegram_id=telegram_id
            )
        else:
            # Если деплой не удался, возвращаем успех генерации, но без URL
            logger.warning("Site generated but deployment failed")
            return GenerateResponse(
                success=True,
                message="Site generated but deployment failed. Please check Deploy API.",
                url=None,
                telegram_id=telegram_id
            )
            
    except Exception as e:
        logger.error(f"Error in generate_and_deploy: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Generation error: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "service": "site-generator"
    }


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "Site Generator API",
        "version": "1.0.0",
        "endpoints": {
            "generate": "/generator",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)

