from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
import secrets
from typing import Annotated

from ..schemas import UserCreate, UserOut, LoginIn, TokenOut, RequestResetIn, ResetPasswordIn, UserRegisterBase as UserRegister
from ..models import User, Token
from ..dependencies import get_db
from ..utils import mint_token, send_email, hash_token, pwd_ctx, get_user_by_refresh_token, normalize_email
from ..config import ACCESS_TOKEN_TTL_MIN, EMAIL_VERIF_TTL_H, RESET_TTL_H, APP_BASE_URL, REFRESH_TOKEN_TTL_DAYS

auth = APIRouter(prefix="/auth", tags=["auth"])

@auth.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserRegister, db: Annotated[AsyncSession, Depends(get_db)]):
    """Регистрирует пользователя и отправляет письмо для подтверждения email."""
    res = await db.execute(select(User).where((User.username == payload.username) | (User.email == normalize_email(payload.email))))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="username или email уже заняты")

    user = User(
        username=payload.username,
        email=normalize_email(payload.email),
        password=pwd_ctx.hash(payload.password),
        role="user",  # Роль всегда "user" при регистрации
        # Позже заменить на False, если нужна верификация email
        is_email_verified=True
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
async def login(body: LoginIn, db: Annotated[AsyncSession, Depends(get_db)], response: Response):
    """Проверяет логин/пароль и выдаёт access- и refresh-токены."""
    res = await db.execute(select(User).where(User.username == body.username))
    user = res.scalar_one_or_none()
    if not user or not pwd_ctx.verify(body.password, user.password):
        raise HTTPException(status_code=401, detail="Неверные учётные данные")
    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Email не подтверждён")
    access_token = await mint_token(db, user, "access", ttl=timedelta(minutes=ACCESS_TOKEN_TTL_MIN))
    refresh_token = await mint_token(db, user, "refresh", ttl=timedelta(days=REFRESH_TOKEN_TTL_DAYS))
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60
    )
    return TokenOut(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_TTL_MIN * 60
    )

@auth.post("/refresh", response_model=TokenOut)
async def refresh_token(request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenOut:
    """Обновляет access-токен по валидному refresh-токену из куки."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token missing")
    user = await get_user_by_refresh_token(db, refresh_token)
    # Отзываем старый refresh-токен
    th = hash_token(refresh_token)
    res = await db.execute(select(Token).where(Token.token_hash == th, Token.type == "refresh"))
    token = res.scalar_one_or_none()
    if token:
        token.revoked = True
        await db.commit()
    # Выдаём новые токены
    access_token = await mint_token(db, user, "access", ttl=timedelta(minutes=ACCESS_TOKEN_TTL_MIN))
    new_refresh_token = await mint_token(db, user, "refresh", ttl=timedelta(days=REFRESH_TOKEN_TTL_DAYS))
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60
    )
    return TokenOut(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_TTL_MIN * 60,
        refresh_token=new_refresh_token
    )

@auth.post("/request-password-reset")
async def request_password_reset(data: RequestResetIn, db: Annotated[AsyncSession, Depends(get_db)]):
    """Создаёт токен/код для сброса пароля и отправляет на email."""
    res = await db.execute(select(User).where(User.email == normalize_email(data.email)))
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