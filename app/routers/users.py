from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Annotated

from ..schemas import UserOut, ChangeUsernameIn, ChangeEmailIn, ChangePasswordIn
from ..models import User
from ..dependencies import get_db, get_current_user
from ..utils import send_email, mint_token, pwd_ctx
from ..config import EMAIL_VERIF_TTL_H, APP_BASE_URL

# Схема безопасности для Bearer-токена
security = HTTPBearer()

users = APIRouter(prefix="/users", tags=["users"])

@users.get("/me", response_model=UserOut, dependencies=[Depends(security)])
async def get_me(current: Annotated[User, Depends(get_current_user)]):
    """Возвращает данные текущего пользователя по access-токену."""
    return UserOut(
        id=current.id,
        username=current.username,
        email=current.email,
        role=current.role,
        is_email_verified=current.is_email_verified,
    )

@users.patch("/me/username", response_model=UserOut, dependencies=[Depends(security)])
async def change_username(data: ChangeUsernameIn, current: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    """Сменяет username на новый при соблюдении валидации и уникальности."""
    exists = await db.execute(select(User).where(User.username == data.new_username))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="username уже занят")
    current.username = data.new_username
    await db.commit()
    await db.refresh(current)
    return UserOut.model_validate(current.__dict__)

@users.patch("/me/email", response_model=UserOut, dependencies=[Depends(security)])
async def change_email(data: ChangeEmailIn, current: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    """Обновляет email и отправляет новое письмо для подтверждения."""
    new_email = str(data.new_email).lower()
    exists = await db.execute(select(User).where(User.email == new_email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="email уже используется")
    current.email = new_email
    current.is_email_verified = False
    await db.commit()
    await db.refresh(current)
    token = await mint_token(db, current, "email_verify", ttl=timedelta(hours=EMAIL_VERIF_TTL_H))
    link = f"{APP_BASE_URL}/auth/verify-email?token={token}"
    send_email(current.email, "Подтверждение нового email", f"Перейдите по ссылке: {link}")
    return UserOut.model_validate(current.__dict__)

@users.patch("/me/password", dependencies=[Depends(security)])
async def change_password(data: ChangePasswordIn, current: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    """Меняет пароль после проверки текущего пароля."""
    if not pwd_ctx.verify(data.current_password, current.password):
        raise HTTPException(status_code=400, detail="Текущий пароль неверен")
    current.password = pwd_ctx.hash(data.new_password)
    await db.commit()
    return {"detail": "Пароль изменён"}