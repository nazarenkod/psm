"""Порты доступа к данным (репозитории) — за Protocol.

Сервисы зависят ТОЛЬКО от этих интерфейсов, а не от SQLAlchemy. Благодаря
этому бизнес-логика юнит-тестируется на фейковых репозиториях без БД.
Реализации на SQLAlchemy живут в ``aifashion.db``.

Изоляция по user_id (требования §10) — инвариант: каждый метод принимает
``user_id`` и обязан фильтровать по нему.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from aifashion.core.models import (
    ConversationTurn,
    ItemStatus,
    PhotoRole,
    UserProfile,
    WardrobeItem,
    WardrobeItemAttrs,
)


class UserRepository(Protocol):
    async def get_or_create(self, telegram_id: int, language: str | None = None) -> UserProfile: ...

    async def save(self, profile: UserProfile) -> UserProfile: ...

    async def set_location(self, user_id: int, lat: float, lon: float) -> None: ...

    async def delete_all(self, user_id: int) -> list[str]:
        """Удалить все данные пользователя. Вернуть ключи блобов для чистки хранилища."""
        ...


class WardrobeRepository(Protocol):
    async def add_item(
        self,
        user_id: int,
        attrs: WardrobeItemAttrs,
        *,
        photo_key: str | None = None,
        embedding: list[float] | None = None,
        status: ItemStatus = ItemStatus.active,
    ) -> WardrobeItem: ...

    async def list_items(self, user_id: int, *, only_active: bool = True) -> list[WardrobeItem]: ...

    async def touch_seen(self, item_id: int) -> None:
        """Обновить last_seen_at — вещь подтверждена в использовании (§4.4)."""
        ...

    async def set_status(self, item_id: int, status: ItemStatus) -> None: ...

    async def find_similar(
        self, user_id: int, embedding: list[float], *, limit: int = 5
    ) -> list[WardrobeItem]:
        """Поиск похожих вещей по эмбеддингу (pgvector) — для проверки дублей (§5)."""
        ...

    async def stale_items(self, user_id: int, *, days: int = 60, limit: int = 5) -> list[WardrobeItem]:
        """Вещи, давно не появлявшиеся — для периодической сверки (§4.4)."""
        ...


class PhotoRepository(Protocol):
    async def add(self, user_id: int, role: PhotoRole, blob_key: str) -> int: ...

    async def selfie_count(self, user_id: int) -> int: ...

    async def evictable_selfie_keys(self, user_id: int, *, keep: int = 5) -> list[str]:
        """Ключи старых селфи сверх лимита ``keep`` — для чистки (§4.5)."""
        ...


class TrendCacheRepository(Protocol):
    """Кэш сводок трендов (тренды меняются медленно — не дёргаем модель каждый раз)."""

    async def get(self, key: str) -> tuple[str, datetime] | None: ...

    async def set(self, key: str, text: str) -> None: ...


class MessageRepository(Protocol):
    """История общения для памяти агента. Привязана к user_id, каскад при /delete."""

    async def add(self, user_id: int, role: str, text: str) -> None: ...

    async def recent(self, user_id: int, *, limit: int = 20) -> list[ConversationTurn]:
        """Последние ``limit`` реплик в хронологическом порядке (старые → новые)."""
        ...
