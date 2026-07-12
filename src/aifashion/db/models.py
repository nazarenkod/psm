"""ORM-модели (SQLAlchemy). Всё привязано к user_id — изоляция (требования §10).

Эмбеддинг вещи (pgvector) — для поиска дублей (§5). Генерация эмбеддингов —
будущий хук (EmbeddingProvider); пока колонка nullable.
"""
from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aifashion.db.base import Base

EMBEDDING_DIM = 1024  # под Voyage-подобные эмбеддинги; меняется при смене модели


class AllowedUser(Base):
    """Белый список Telegram ID (требования §10)."""

    __tablename__ = "allowed_users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """Профиль. id = Telegram ID (без отдельной регистрации, §10)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    color_type: Mapped[str | None] = mapped_column(String, nullable=True)
    contrast: Mapped[str | None] = mapped_column(String, nullable=True)
    silhouette_json: Mapped[str | None] = mapped_column(String, nullable=True)
    sex: Mapped[str | None] = mapped_column(String, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lifestyle: Mapped[str | None] = mapped_column(String, nullable=True)
    dress_code: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    items: Mapped[list[WardrobeItemORM]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    photos: Mapped[list[PhotoORM]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class WardrobeItemORM(Base):
    __tablename__ = "wardrobe_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    seasonality: Mapped[str | None] = mapped_column(String, nullable=True)
    style: Mapped[str | None] = mapped_column(String, nullable=True)
    brand: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")
    photo_key: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="items")


class TrendCacheORM(Base):
    """Кэш сводок трендов по контексту (сезон/пол/стиль)."""

    __tablename__ = "trend_cache"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    text: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MessageORM(Base):
    """История общения (память агента). Каскадно удаляется с пользователем (§10)."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PhotoORM(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String)  # PhotoRole
    blob_key: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="photos")
