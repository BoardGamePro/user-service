# Auth Service

Сервис аутентификации и управления пользователями на FastAPI.

## Запуск проекта

### Вариант 1: Запуск с Docker (рекомендуется для быстрого старта)

1. Убедитесь, что Docker и Docker Compose установлены.

2. Запустите сервисы:
```bash
docker-compose up --build
```
Это запустит базу данных PostgreSQL и веб-приложение. Сервер будет доступен на `http://localhost:8000`.

Переменные окружения берутся из `docker-compose.yml`.

### Вариант 2: Локальный запуск

#### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd auth-service
```

#### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

#### 3. Настройка переменных окружения
Создайте файл `.env` в корне проекта и настройте переменные:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/auth_db
ACCESS_TOKEN_TTL_MIN=60
REFRESH_TOKEN_TTL_DAYS=7
EMAIL_VERIF_TTL_H=24
RESET_TTL_H=2
APP_BASE_URL=http://localhost:8000
SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-password
SMTP_FROM=no-reply@example.com
SMTP_TLS=true
```

#### 4. Настройка Alembic
Скопируйте шаблон конфигурации Alembic:
```bash
cp alembic.ini.example alembic.ini
```
Alembic использует переменную окружения `DATABASE_URL` из `.env`.

#### 5. Запуск базы данных
Если используете Docker для базы данных:
```bash
docker-compose up -d db
```
Или настройте PostgreSQL локально.

#### 6. Запуск миграций базы данных
```bash
alembic upgrade head
```

#### 7. Запуск сервера
```bash
uvicorn app.main:app --reload
```
Сервер будет доступен на `http://localhost:8000`.

### API документация
После запуска перейдите на `http://localhost:8000/docs` для просмотра Swagger UI.

## Тестирование
```bash
python -m pytest tests/ -v
```

## Структура проекта
- `app/` - основной код приложения
- `tests/` - тесты
- `alembic/` - миграции базы данных
