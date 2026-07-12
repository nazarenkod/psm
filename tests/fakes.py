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

    async def parse(self, *, system, prompt, schema, images=None, history=None):
        self.calls.append(
            {
                "system": system,
                "prompt": prompt,
                "schema": schema,
                "images": images,
                "history": history,
            }
        )
        assert self.responses, "FakeLLM: нет заготовленного ответа"
        r = self.responses.pop(0)
        if isinstance(r, BaseModel):
            return r
        return schema.model_validate(r)

    async def complete(self, *, system, prompt, images=None, history=None) -> str:
        self.calls.append({"system": system, "prompt": prompt, "images": images, "history": history})
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
        self.similar: list[WardrobeItem] = []   # что вернёт find_similar
        self.embeddings: dict[int, list[float] | None] = {}

    async def add_item(self, user_id, attrs, *, photo_key=None, embedding=None, status=ItemStatus.active):
        self._next += 1
        item = WardrobeItem(
            id=self._next, user_id=user_id, attrs=attrs, status=status, photo_key=photo_key
        )
        self.items.append(item)
        self.embeddings[item.id] = embedding
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
        return self.similar[:limit]

    async def stale_items(self, user_id, *, days=60, limit=5):
        return []


class FakeEmbedder:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.texts.append(text)
        return [float(len(text)), 0.0, 1.0]


class FakeWeather:
    def __init__(self, data: dict | None = None) -> None:
        self.data = data if data is not None else {"temperature_2m": 12, "wind_speed_10m": 3}
        self.calls: list[tuple[float, float]] = []

    async def current(self, lat: float, lon: float) -> dict:
        self.calls.append((lat, lon))
        return self.data


class FakeMessageRepo:
    def __init__(self) -> None:
        self.records: list[tuple[int, str, str]] = []
        self.preload: list = []  # list[ConversationTurn] возвращается из recent

    async def add(self, user_id: int, role: str, text: str) -> None:
        self.records.append((user_id, role, text))

    async def recent(self, user_id: int, *, limit: int = 20):
        return list(self.preload)


class FakeImageGen:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, size: str = "1024x1024") -> bytes:
        self.prompts.append(prompt)
        return b"PNGDATA"


class FakeTrendProvider:
    def __init__(self, brief: str = "оверсайз пальто, бордовый акцент") -> None:
        self.brief_text = brief
        self.calls: list[str] = []

    async def current_brief(self, context: str) -> str:
        self.calls.append(context)
        return self.brief_text


class FakeTrendCache:
    def __init__(self) -> None:
        self.store: dict[str, tuple[str, "datetime"]] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, text: str) -> None:
        from datetime import datetime, timezone

        self.store[key] = (text, datetime.now(timezone.utc))


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
    "FakeEmbedder",
    "FakeWeather",
    "FakeTrendProvider",
    "FakeTrendCache",
    "FakeMessageRepo",
    "FakeImageGen",
    "PhotoRole",
    "img",
    "attrs",
]
