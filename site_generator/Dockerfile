FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Переменные окружения (будут переопределены через docker-compose или при запуске)
ENV PYTHONUNBUFFERED=1
ENV PORT=3000
ENV OPENROUTER_API_KEY=""
ENV DEPLOY_API_URL="http://deploy-api:8000"

# Expose порт
EXPOSE 3000

# Запускаем API
CMD ["python", "api.py"]

