from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from .database import SessionLocal
from .utils import get_user_by_access_token, get_user_by_refresh_token
from .models import User

async def get_db() -> AsyncSession:
    """Даёт сессию БД и закрывает по завершении запроса."""
    async with SessionLocal() as session:
        yield session

async def get_current_user(
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> User:
    """Извлекает Bearer opaque токен из заголовка и отдаёт пользователя."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется Bearer токен")
    token = authorization.split(" ", 1)[1].strip()
    return await get_user_by_access_token(db, token)

async def get_user_by_refresh(
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> User:
    """Извлекает Bearer refresh-токен из заголовка и отдаёт пользователя."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется Bearer refresh-токен")
    token = authorization.split(" ", 1)[1].strip()
    return await get_user_by_refresh_token(db, token)