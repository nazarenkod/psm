"""Фейковые реализации провайдеров и репозиториев для юнит-тестов.

Благодаря Protocol-портам бизнес-логика тестируется без БД, сети и Anthropic.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from aifashion.core.models import (
    ImageInput,
    ItemStatus,
    PhotoRole,
    UserProfile,
    WardrobeItem,
    WardrobeItemAttrs,
)


class FakeLLM:
    """LLMProvider, отдающий заранее заготовленные ответы и пишущий вызовы."""

    def __init__(self, responses: list[Any] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[dict] = []

    async def parse(self, *, system, prompt, schema, images=None):
        self.calls.append(
            {"system": system, "prompt": prompt, "schema": schema, "images": images}
        )
        assert self.responses, "FakeLLM: нет заготовленного ответа"
        r = self.responses.pop(0)
        if isinstance(r, BaseModel):
            return r
        return schema.model_validate(r)

    async def complete(self, *, system, prompt, images=None) -> str:
        self.calls.append({"system": system, "prompt": prompt, "images": images})
        return "ok"


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted_prefixes: list[str] = []

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        self.objects[key] = data
        return key

    async def delete_prefix(self, prefix: str) -> int:
        keys = [k for k in self.objects if k.startswith(prefix)]
        for k in keys:
            del self.objects[k]
        self.deleted_prefixes.append(prefix)
        return len(keys)


class FakeWardrobeRepo:
    def __init__(self) -> None:
        self.items: list[WardrobeItem] = []
        self._next = 0
        self.touched: list[int] = []

    async def add_item(self, user_id, attrs, *, photo_key=None, embedding=None, status=ItemStatus.active):
        self._next += 1
        item = WardrobeItem(
            id=self._next, user_id=user_id, attrs=attrs, status=status, photo_key=photo_key
        )
        self.items.append(item)
        return item

    async def list_items(self, user_id, *, only_active=True):
        return [
            i
            for i in self.items
            if i.user_id == user_id and (not only_active or i.status == ItemStatus.active)
        ]

    async def touch_seen(self, item_id):
        self.touched.append(item_id)

    async def set_status(self, item_id, status):
        for i in self.items:
            if i.id == item_id:
                i.status = status

    async def find_similar(self, user_id, embedding, *, limit=5):
        return []

    async def stale_items(self, user_id, *, days=60, limit=5):
        return []


class FakeUserRepo:
    def __init__(self) -> None:
        self.users: dict[int, UserProfile] = {}
        self.deleted: list[int] = []

    async def get_or_create(self, telegram_id, language=None):
        if telegram_id not in self.users:
            self.users[telegram_id] = UserProfile(id=telegram_id, language=language)
        return self.users[telegram_id]

    async def save(self, profile):
        self.users[profile.id] = profile
        return profile

    async def set_location(self, user_id, lat, lon):
        u = self.users[user_id]
        u.lat, u.lon = lat, lon

    async def delete_all(self, user_id):
        self.deleted.append(user_id)
        self.users.pop(user_id, None)
        return [f"users/{user_id}/wardrobe/x"]


def img() -> ImageInput:
    return ImageInput(data_b64="aGVsbG8=")  # "hello" в base64


def attrs(category="sweater", **kw) -> WardrobeItemAttrs:
    return WardrobeItemAttrs(category=category, **kw)


__all__ = [
    "FakeLLM",
    "FakeStorage",
    "FakeWardrobeRepo",
    "FakeUserRepo",
    "PhotoRole",
    "img",
    "attrs",
]
