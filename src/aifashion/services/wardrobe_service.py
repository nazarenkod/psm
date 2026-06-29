"""Сервис гардероба (требования §4.3, §4.4, §5).

Зависит от портов (репозиторий) и провайдеров (LLM, хранилище, опц. эмбеддер) —
через Protocol, поэтому юнит-тестируется на фейках. Эмбеддер опционален: без него
вещи сохраняются без вектора, поиск дублей мягко деградирует.
"""
from __future__ import annotations

import base64
import uuid

from aifashion.core.models import (
    ExtractedItems,
    ImageInput,
    WardrobeItem,
    WardrobeItemAttrs,
)
from aifashion.core.ports import WardrobeRepository
from aifashion.core.signatures import item_signature_text
from aifashion.providers.base import EmbeddingProvider, LLMProvider, StorageProvider

_EXTRACT_ONE = (
    "Извлеки характеристики ОДНОЙ вещи на фото: категория, цвет, материал, "
    "сезонность, стиль, бренд, цена (если видно). Чего не видно — оставь пустым."
)
_EXTRACT_LOOK = (
    "Это образ (лук). Извлеки ВСЕ вещи на нём как отдельные элементы со своими "
    "характеристиками. Не выдумывай то, чего не видно."
)


class WardrobeService:
    def __init__(
        self,
        repo: WardrobeRepository,
        llm: LLMProvider,
        storage: StorageProvider,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self._repo = repo
        self._llm = llm
        self._storage = storage
        self._embedder = embedder

    async def extract_attrs(self, image: ImageInput) -> WardrobeItemAttrs:
        """Распознать характеристики одной вещи по фото (без сохранения)."""
        return await self._llm.parse(
            system=_EXTRACT_ONE,
            prompt="Опиши вещь на фото.",
            schema=WardrobeItemAttrs,
            images=[image],
        )

    async def add_from_photo(self, user_id: int, image: ImageInput) -> WardrobeItem:
        """Добавить одну вещь по фото (§4.3, способ 1)."""
        attrs = await self.extract_attrs(image)
        key = await self._store_photo(user_id, image)
        return await self._repo.add_item(
            user_id, attrs, photo_key=key, embedding=await self._embed(attrs)
        )

    async def parse_look(self, user_id: int, image: ImageInput) -> list[WardrobeItem]:
        """Разбор лука: вытащить все вещи разом (§4.3, способ 2)."""
        extracted = await self._llm.parse(
            system=_EXTRACT_LOOK,
            prompt="Перечисли все вещи образа.",
            schema=ExtractedItems,
            images=[image],
        )
        created: list[WardrobeItem] = []
        for attrs in extracted.items:
            created.append(
                await self._repo.add_item(user_id, attrs, embedding=await self._embed(attrs))
            )
        return created

    async def find_duplicates(
        self, user_id: int, attrs: WardrobeItemAttrs, *, limit: int = 5
    ) -> list[WardrobeItem]:
        """Похожие вещи в гардеробе по эмбеддингу (§5). Без эмбеддера — пусто."""
        if self._embedder is None:
            return []
        vector = await self._embedder.embed(item_signature_text(attrs))
        return await self._repo.find_similar(user_id, vector, limit=limit)

    async def summary_for_prompt(self, user_id: int) -> list[WardrobeItem]:
        """Активный гардероб для контекста движков (работает на неполном, §4.3)."""
        return await self._repo.list_items(user_id, only_active=True)

    async def confirm_worn(self, item_id: int) -> None:
        """Вещь появилась в использовании — обновить last_seen_at (§4.4)."""
        await self._repo.touch_seen(item_id)

    async def _embed(self, attrs: WardrobeItemAttrs) -> list[float] | None:
        if self._embedder is None:
            return None
        return await self._embedder.embed(item_signature_text(attrs))

    async def _store_photo(self, user_id: int, image: ImageInput) -> str:
        key = f"users/{user_id}/wardrobe/{uuid.uuid4().hex}"
        data = base64.b64decode(image.data_b64)
        return await self._storage.put(key, data, image.media_type)
