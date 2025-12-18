from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    """Модель пользователя: хранит учётные данные, роль, описание и настройки приватности."""
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(PGUUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bio: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    is_profile_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_collection_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tokens: Mapped[list["Token"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Token(Base):
    """Модель токена: хранит непрозрачные токены разных типов с TTL."""
    __tablename__ = "tokens"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String, index=True, unique=True)
    type: Mapped[str] = mapped_column(String)  # access | email_verify | reset
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="tokens")

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_token_hash"),
    )


class Comment(Base):
    """Модель комментария: хранит комментарии пользователей к страницам правил игр."""
    __tablename__ = "comments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    page: Mapped[str] = mapped_column(String, nullable=False, index=True)
    comment_text: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))
