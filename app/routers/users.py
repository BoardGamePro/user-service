from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from fastapi.security import HTTPBearer
from sqlalchemy import select, asc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Annotated, Optional
from pydantic import BaseModel

from ..schemas import UserOut, UserPublicOut, ChangeUsernameIn, ChangeEmailIn, ChangePasswordIn
from ..models import User
from ..dependencies import get_db, get_current_user
from ..utils import send_email, mint_token, pwd_ctx
from ..config import EMAIL_VERIF_TTL_H, APP_BASE_URL

security = HTTPBearer()

users = APIRouter(prefix="/users", tags=["users"])

@users.get("/me", response_model=UserOut, dependencies=[Depends(security)])
async def get_me(current: Annotated[User, Depends(get_current_user)]):
    """
    Возвращает данные текущего пользователя по access-токену.
    """
    return UserOut(
        id=str(current.id),
        username=str(current.username),
        email=current.email,
        role=str(current.role),
        is_email_verified=current.is_email_verified,
        bio=str(current.bio) if current.bio is not None else None,
        is_profile_public=bool(current.is_profile_public),
        is_collection_public=bool(current.is_collection_public),
    )

@users.get("/{username}", response_model=UserPublicOut)
async def get_user_profile(username: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Получить публичный профиль пользователя по username (с учётом приватности).
    """
    res = await db.execute(select(User).where(User.username == username))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not user.is_profile_public:
        raise HTTPException(status_code=403, detail="Профиль скрыт настройками приватности")
    return UserPublicOut(
        id=str(user.id),
        username=str(user.username),
        bio=str(user.bio) if user.bio is not None else None,
        is_profile_public=bool(user.is_profile_public),
        is_collection_public=bool(user.is_collection_public),
        role=str(user.role),
    )

@users.get("/id/{user_id}", response_model=UserPublicOut)
async def get_user_by_id(user_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Получить публичный профиль пользователя по id.
    """
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not user.is_profile_public:
        raise HTTPException(status_code=403, detail="Профиль скрыт настройками приватности")
    return UserPublicOut(
        id=str(user.id),
        username=str(user.username),
        bio=str(user.bio) if user.bio is not None else None,
        is_profile_public=bool(user.is_profile_public),
        is_collection_public=bool(user.is_collection_public),
        role=str(user.role),
    )

@users.patch("/me/username", response_model=UserOut, dependencies=[Depends(security)])
async def change_username(data: ChangeUsernameIn, current: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Сменяет username на новый при соблюдении валидации и уникальности.
    """
    exists = await db.execute(select(User).where(User.username == data.new_username))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="username уже занят")
    current.username = data.new_username
    await db.commit()
    await db.refresh(current)
    return UserOut(
        id=str(current.id),
        username=str(current.username),
        email=current.email,
        role=str(current.role),
        is_email_verified=current.is_email_verified,
        bio=str(current.bio) if current.bio is not None else None,
        is_profile_public=bool(current.is_profile_public),
        is_collection_public=bool(current.is_collection_public),
    )

@users.patch("/me/email", response_model=UserOut, dependencies=[Depends(security)])
async def change_email(data: ChangeEmailIn, current: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Обновляет email и отправляет новое письмо для подтверждения.
    """
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
    send_email(str(current.email), "Подтверждение нового email", f"Перейдите по ссылке: {link}")
    return UserOut(
        id=str(current.id),
        username=str(current.username),
        email=current.email,
        role=str(current.role),
        is_email_verified=current.is_email_verified,
        bio=str(current.bio) if current.bio is not None else None,
        is_profile_public=bool(current.is_profile_public),
        is_collection_public=bool(current.is_collection_public),
    )

@users.patch("/me/password", dependencies=[Depends(security)])
async def change_password(data: ChangePasswordIn, current: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    """Меняет пароль после проверки текущего пароля."""
    if not pwd_ctx.verify(data.current_password, current.password):
        raise HTTPException(status_code=400, detail="Текущий пароль неверен")
    current.password = pwd_ctx.hash(data.new_password)
    await db.commit()
    return {"detail": "Пароль изменён"}

class ChangeProfileIn(BaseModel):
    bio: Optional[str] = None
    is_profile_public: Optional[bool] = None
    is_collection_public: Optional[bool] = None

@users.patch("/me/profile", response_model=UserOut, dependencies=[Depends(security)])
async def change_profile(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    data: ChangeProfileIn = Body(...)
):
    """Изменяет bio и настройки приватности текущего пользователя."""
    if data.bio is not None:
        current.bio = data.bio
    if data.is_profile_public is not None:
        current.is_profile_public = data.is_profile_public
    if data.is_collection_public is not None:
        current.is_collection_public = data.is_collection_public
    await db.commit()
    await db.refresh(current)
    return UserOut(
        id=str(current.id),
        username=str(current.username),
        email=current.email,
        role=str(current.role),
        is_email_verified=current.is_email_verified,
        bio=str(current.bio) if current.bio is not None else None,
        is_profile_public=bool(current.is_profile_public),
        is_collection_public=bool(current.is_collection_public),
    )

from fastapi.responses import JSONResponse

@users.post("/logout", dependencies=[Depends(security)])
async def logout(
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Отзывает refresh-токен и удаляет его из куки."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        from ..utils import hash_token
        from ..models import Token
        th = hash_token(refresh_token)
        res = await db.execute(select(Token).where(Token.token_hash == th, Token.type == "refresh", Token.user_id == current.id))
        token = res.scalar_one_or_none()
        if token:
            token.revoked = True
            await db.commit()
    response = JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "Logged out successfully"})
    response.delete_cookie("refresh_token")
    return response

@users.delete("/me", dependencies=[Depends(security)])
async def delete_account(current: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    """Удаляет аккаунт текущего пользователя."""
    await db.delete(current)
    await db.commit()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "Account deleted"})

@users.get("/", response_model=list[UserOut])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100, description="Сколько пользователей вернуть"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации")
):
    """
    Получить список аккаунтов с пагинацией и сортировкой по алфавиту (username).
    """
    res = await db.execute(
        select(User).order_by(asc(User.username)).offset(offset).limit(limit)
    )
    users_list = res.scalars().all()
    return [UserOut(
        id=str(u.id),
        username=str(u.username),
        email=u.email,
        role=str(u.role),
        is_email_verified=u.is_email_verified,
        bio=str(u.bio) if u.bio is not None else None,
        is_profile_public=bool(u.is_profile_public),
        is_collection_public=bool(u.is_collection_public),
    ) for u in users_list]
