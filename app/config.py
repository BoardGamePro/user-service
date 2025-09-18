import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://dev:devpass@localhost:5432/auth_db")
ACCESS_TOKEN_TTL_MIN = int(os.getenv("ACCESS_TOKEN_TTL_MIN", "60"))
REFRESH_TOKEN_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "7"))  # Новый параметр
EMAIL_VERIF_TTL_H = int(os.getenv("EMAIL_VERIF_TTL_H", "24"))
RESET_TTL_H = int(os.getenv("RESET_TTL_H", "2"))
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@example.com")
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"