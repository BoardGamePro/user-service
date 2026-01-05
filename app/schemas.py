import re
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
ALLOWED_ROLES = {"user", "admin"}

class UserRegisterBase(BaseModel):
    """Базовая схема для регистрации с общими полями."""
    username: Annotated[str, Field(..., description="Уникальное имя пользователя")]
    email: Annotated[EmailStr, Field(..., description="Email пользователя")]
    password: Annotated[str, Field(min_length=8, max_length=128, description="Пароль пользователя")]

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("username должен быть 3-32 символа: латиница, цифры, подчёркивание")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8 or len(v) > 128:
            raise ValueError("пароль должен быть 8-128 символов")
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("пароль должен содержать буквы и цифры")
        return v

class UserBase(BaseModel):
    """Базовая схема пользователя с общими полями."""
    role: Annotated[Literal["user", "admin"], Field(default="user", description="Роль пользователя")]
    bio: Optional[str] = None
    is_profile_public: bool = True
    is_collection_public: bool = True

class UserCreate(UserRegisterBase, UserBase):
    """Схема для создания пользователя с паролем."""
    pass

class UserOut(BaseModel):
    """Схема для вывода данных пользователя."""
    id: str
    username: str
    email: EmailStr
    role: str
    is_email_verified: bool
    bio: Optional[str] = None
    is_profile_public: bool
    is_collection_public: bool

class LoginIn(BaseModel):
    """Схема для входа: username и пароль."""
    username: str
    password: str

class TokenOut(BaseModel):
    """Схема для вывода токенов."""
    access_token: str
    expires_in: int
    refresh_token: str | None = None  # refresh_token теперь опционален
    token_type: Literal["opaque"] = "opaque"

class RefreshTokenIn(BaseModel):  # схема для запроса обновления
    """Схема для обновления токена."""
    refresh_token: str

class ChangeUsernameIn(BaseModel):
    """Схема для изменения имени пользователя."""
    new_username: str
    @field_validator("new_username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("username должен быть 3-32 символа: латиница, цифры, подчёркивание")
        return v

class ChangeEmailIn(BaseModel):
    """Схема для изменения email пользователя."""
    new_email: EmailStr

class ChangePasswordIn(BaseModel):
    """Схема для изменения пароля пользователя."""
    current_password: str
    new_password: str
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8 or len(v) > 128:
            raise ValueError("пароль должен быть 8-128 символов")
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("пароль должен содержать буквы и цифры")
        return v

class RequestResetIn(BaseModel):
    """Схема для запроса сброса пароля."""
    email: EmailStr

class ResetPasswordIn(BaseModel):
    """Схема для сброса пароля."""
    token: str | None = None
    code: str | None = None
    new_password: str
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8 or len(v) > 128:
            raise ValueError("пароль должен быть 8-128 символов")
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("пароль должен содержать буквы и цифры")
        return v

class BlacklistEntry(BaseModel):
    """Схема для чёрного списка пользователей."""
    id: int
    user_id: str
    blocked_user_id: str

class BlacklistAddIn(BaseModel):
    """Схема для добавления пользователя в чёрный список."""
    blocked_user_id: str

class UserPublicOut(BaseModel):
    """Схема для публичного отображения пользователя."""
    id: str
    username: str
    bio: Optional[str] = None
    is_profile_public: bool
    is_collection_public: bool
    role: str


class CommentCreate(BaseModel):
    """Схема для создания комментария."""
    game_name: str
    page: str
    title: Annotated[str, Field(min_length=1, max_length=200)]
    comment_text: Annotated[str, Field(min_length=1, max_length=1000)]


class CommentOut(BaseModel):
    """Схема для вывода комментария."""
    id: str
    user_id: str
    username: str
    game_name: str
    page: str
    title: str
    comment_text: str
    created_at: str
    updated_at: str


class CommentUpdate(BaseModel):
    """Схема для обновления комментария."""
    title: Annotated[str, Field(min_length=1, max_length=200)]
    comment_text: Annotated[str, Field(min_length=1, max_length=1000)]
