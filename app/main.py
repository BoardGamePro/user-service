from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.security import HTTPBearer
from .routers.auth import auth
from .routers.users import users
from .database import create_all

@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.include_router(auth)
app.include_router(users)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}