# Базовый образ с Python 3.11
FROM python:3.11-slim

# Определим рабочую директорию
WORKDIR /app

# Установим зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

# Переменные окружения для FastAPI
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Команда по умолчанию: запуск миграций и приложения
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
