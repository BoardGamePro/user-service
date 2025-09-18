from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Annotated, Literal
import re

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
ALLOWED_ROLES = {"user", "admin"}

class UserBase(BaseModel):
    username: Annotated[str, Field(..., description="Уникальное имя пользователя")]
    email: Annotated[EmailStr, Field(..., description="Email пользователя")]
    role: Annotated[Literal["user", "admin"], Field(default="user", description="Роль пользователя")]

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("username должен быть 3-32 символа: латиница, цифры, подчёркивание")
        return v

class UserCreate(UserBase):
    password: Annotated[str, Field(min_length=8, max_length=128, description="Пароль пользователя")]

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8 or len(v) > 128:
            raise ValueError("пароль должен быть 8-128 символов")
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("пароль должен содержать буквы и цифры")
        return v

class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
    role: str
    is_email_verified: bool

class LoginIn(BaseModel):
    username: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str  # Добавляем refresh-токен
    token_type: Literal["opaque"] = "opaque"
    expires_in: int

class RefreshTokenIn(BaseModel):  # Новая схема для запроса обновления
    refresh_token: str

class ChangeUsernameIn(BaseModel):
    new_username: str
    @field_validator("new_username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("username должен быть 3-32 символа: латиница, цифры, подчёркивание")
        return v

class ChangeEmailIn(BaseModel):
    new_email: EmailStr

class ChangePasswordIn(BaseModel):
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
    email: EmailStr

class ResetPasswordIn(BaseModel):
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