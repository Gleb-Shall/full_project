FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для обработки изображений
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание директорий
RUN mkdir -p user_data

# Запуск бота
CMD ["python", "bot.py"]

