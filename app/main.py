from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from .database import create_all
from .routers.auth import auth
from .routers.comments import comments
from .routers.users import users

load_dotenv()

origins = [
    "http://localhost:3000",
    "http://localhost",
    "http://localhost:8080",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Создание таблиц базы данных при запуске приложения."""
    await create_all()
    yield

# Схема безопасности для Swagger UI
security = HTTPBearer()

app = FastAPI(
    title="Opaque Auth Service",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[{"name": "auth", "description": "Authentication operations"}, {"name": "users", "description": "User operations"}]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth)
app.include_router(users)
app.include_router(comments)

@app.get("/healthz")
async def healthz():
    """Проверка здоровья сервиса."""
    return {"status": "ok"}