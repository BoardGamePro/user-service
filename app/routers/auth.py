from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import secrets
from typing import Annotated

from ..schemas import UserCreate, UserOut, LoginIn, TokenOut, RequestResetIn, ResetPasswordIn, RefreshTokenIn
from ..models import User, Token
from ..dependencies import get_db
from ..utils import mint_token, send_email, hash_token, pwd_ctx, get_user_by_refresh_token  # Добавлен импорт
from ..config import ACCESS_TOKEN_TTL_MIN, EMAIL_VERIF_TTL_H, RESET_TTL_H, APP_BASE_URL, REFRESH_TOKEN_TTL_DAYS

auth = APIRouter(prefix="/auth", tags=["auth"])

@auth.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """Регистрирует пользователя и отправляет письмо для подтверждения email."""
    res = await db.execute(select(User).where((User.username == payload.username) | (User.email == payload.email)))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="username или email уже заняты")

    if payload.role not in {"user", "admin"}:
        raise HTTPException(status_code=422, detail="Недопустимая роль")

    user = User(
        username=payload.username,
        email=str(payload.email).lower(),
        password=pwd_ctx.hash(payload.password),
        role=payload.role,

        # Временно поставил тру, тк еще не добавил smtp
        is_email_verified=True
        # is_email_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = await mint_token(db, user, "email_verify", ttl=timedelta(hours=EMAIL_VERIF_TTL_H))
    link = f"{APP_BASE_URL}/auth/verify-email?token={token}"
    send_email(user.email, "Подтверждение email", f"Перейдите по ссылке для подтверждения: {link}")

    return UserOut.model_validate(user.__dict__)

@auth.get("/verify-email")
async def verify_email(token: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Помечает email как подтверждённый по валидному токену из письма."""
    th = hash_token(token)
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(Token, User).join(User, Token.user_id == User.id).where(
            Token.token_hash == th, Token.type == "email_verify", Token.revoked == False, Token.expires_at > now
        )
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=400, detail="Неверный или просроченный токен")
    t: Token
    u: User
    t, u = row
    u.is_email_verified = True
    t.revoked = True
    await db.commit()
    return {"detail": "Email подтверждён"}

@auth.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: Annotated[AsyncSession, Depends(get_db)]):
    """Проверяет логин/пароль и выдаёт access- и refresh-токены."""
    res = await db.execute(select(User).where(User.username == body.username))
    user = res.scalar_one_or_none()
    if not user or not pwd_ctx.verify(body.password, user.password):
        raise HTTPException(status_code=401, detail="Неверные учётные данные")
    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Email не подтверждён")
    access_token = await mint_token(db, user, "access", ttl=timedelta(minutes=ACCESS_TOKEN_TTL_MIN))
    refresh_token = await mint_token(db, user, "refresh", ttl=timedelta(days=REFRESH_TOKEN_TTL_DAYS))
    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_TTL_MIN * 60
    )

@auth.post("/refresh", response_model=TokenOut)
async def refresh_token(data: RefreshTokenIn, db: Annotated[AsyncSession, Depends(get_db)]):
    """Обновляет access-токен по валидному refresh-токену."""
    user = await get_user_by_refresh_token(db, data.refresh_token)
    # Отзываем старый refresh-токен
    th = hash_token(data.refresh_token)
    res = await db.execute(select(Token).where(Token.token_hash == th, Token.type == "refresh"))
    token = res.scalar_one_or_none()
    if token:
        token.revoked = True
        await db.commit()
    # Выдаём новые токены
    access_token = await mint_token(db, user, "access", ttl=timedelta(minutes=ACCESS_TOKEN_TTL_MIN))
    refresh_token = await mint_token(db, user, "refresh", ttl=timedelta(days=REFRESH_TOKEN_TTL_DAYS))
    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_TTL_MIN * 60
    )

@auth.post("/request-password-reset")
async def request_password_reset(data: RequestResetIn, db: Annotated[AsyncSession, Depends(get_db)]):
    """Создаёт токен/код для сброса пароля и отправляет на email."""
    res = await db.execute(select(User).where(User.email == str(data.email).lower()))
    user = res.scalar_one_or_none()
    if not user:
        return {"detail": "Если email существует, инструкция отправлена"}
    token = await mint_token(db, user, "reset", ttl=timedelta(hours=RESET_TTL_H))
    link = f"{APP_BASE_URL}/auth/reset-password?token={token}"
    code = f"{secrets.randbelow(10**6):06d}"
    await mint_token(db, user, "reset", ttl=timedelta(hours=RESET_TTL_H), raw_token=code)
    send_email(
        user.email,
        "Сброс пароля",
        f"Для сброса перейдите по ссылке: {link}\nИли введите код: {code}"
    )
    return {"detail": "Если email существует, инструкция отправлена"}

@auth.post("/reset-password")
async def reset_password(data: ResetPasswordIn, db: Annotated[AsyncSession, Depends(get_db)]):
    """Сбрасывает пароль по валидному токену из письма или коду."""
    if not data.token and not data.code:
        raise HTTPException(status_code=400, detail="Нужно передать token или code")

    now = datetime.now(timezone.utc)
    token_hashes: list[str] = []
    if data.token:
        token_hashes.append(hash_token(data.token))
    if data.code:
        token_hashes.append(hash_token(data.code))

    res = await db.execute(
        select(Token, User)
        .join(User, Token.user_id == User.id)
        .where(Token.token_hash.in_(token_hashes), Token.type == "reset", Token.revoked == False, Token.expires_at > now)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=400, detail="Неверный или просроченный токен/код")
    t, u = row
    u.password = pwd_ctx.hash(data.new_password)
    t.revoked = True
    await db.commit()
    return {"detail": "Пароль сброшен"}