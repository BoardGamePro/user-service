import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import smtplib
from typing import Optional
from passlib.context import CryptContext

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Token
from .config import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM, SMTP_TLS

# Инициализация контекста для хеширования паролей
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_token(raw: str) -> str:
    """Возвращает SHA-256 хеш токена (не храним токен в открытом виде)."""
    return hashlib.sha256(raw.encode()).hexdigest()

def send_email(to: str, subject: str, text: str) -> None:
    """Отправляет письмо через SMTP; если SMTP не настроен — выводит в консоль."""
    if not SMTP_HOST:
        print("\n=== EMAIL (mock) ===\nTo:", to, "\nSubject:", subject, "\n", text, "\n====================\n")
        return
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        if SMTP_TLS:
            s.starttls()
        if SMTP_USERNAME and SMTP_PASSWORD:
            s.login(SMTP_USERNAME, SMTP_PASSWORD)
        s.send_message(msg)

async def mint_token(session: AsyncSession, user: User, ttype: str, ttl: timedelta, raw_token: Optional[str] = None) -> str:
    """Создаёт новый opaque-токен указанного типа и сохраняет его хеш и TTL. Если raw_token передан — использует его вместо генерации."""
    if raw_token is None:
        raw_token = secrets.token_urlsafe(48)
    token_h = hash_token(raw_token)
    expires = datetime.now(timezone.utc) + ttl
    session.add(Token(user_id=user.id, token_hash=token_h, type=ttype, expires_at=expires, revoked=False))
    await session.commit()
    return raw_token

async def get_user_by_access_token(session: AsyncSession, token: str) -> User:
    """Возвращает пользователя по access-токену (проверяет хеш и TTL)."""
    th = hash_token(token)
    now = datetime.now(timezone.utc)
    stmt = (
        select(User)
        .join(Token, Token.user_id == User.id)
        .where(Token.token_hash == th, Token.type == "access", Token.revoked == False, Token.expires_at > now)
    )
    res = await session.execute(stmt)
    user: User | None = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный или просроченный токен")
    return user

async def get_user_by_refresh_token(session: AsyncSession, token: str) -> User:
    """Возвращает пользователя по refresh-токену (проверяет хеш и TTL)."""
    th = hash_token(token)
    now = datetime.now(timezone.utc)
    stmt = (
        select(User)
        .join(Token, Token.user_id == User.id)
        .where(Token.token_hash == th, Token.type == "refresh", Token.revoked == False, Token.expires_at > now)
    )
    res = await session.execute(stmt)
    user: User | None = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный или просроченный refresh-токен")
    return user