"""Интерфейсы внешних сервисов (раздел 10.2 — «внешние сервисы за тонкой обёрткой»).

Бизнес-логика зависит ТОЛЬКО от этих Protocol'ов, а не от Anthropic/OpenAI/etc.
Сменить провайдера или модель = добавить реализацию + поменять конфиг.
"""
from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from aifashion.core.models import ConversationTurn, ImageInput

TModel = TypeVar("TModel", bound=BaseModel)


class LLMProvider(Protocol):
    """Мультимодальный провайдер: и «видит» фото, и рассуждает.

    Одна абстракция на vision+reasoning — потому что для качественного
    (не количественного) портрета силуэта (раздел 4.1) мультимодальный LLM
    подходит лучше отдельного CV-пайплайна. При желании vision можно вынести
    в отдельную реализацию, не трогая вызывающий код.

    ``history`` — прошлые реплики диалога для контекста (память агента).
    """

    async def parse(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[TModel],
        images: list[ImageInput] | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> TModel:
        """Вернуть структурированный ответ, провалидированный по ``schema``."""
        ...

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        images: list[ImageInput] | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> str:
        """Вернуть свободный текстовый ответ."""
        ...


class ImageGenProvider(Protocol):
    """Генерация изображений (капсулы/образы). Claude не умеет — идёт через OpenAI.

    Отдельный порт: рассуждения остаются на LLM, рендер — на генераторе картинок.
    """

    async def generate(self, prompt: str, *, size: str = "1024x1024") -> bytes:
        ...


class WeatherProvider(Protocol):
    """Источник погоды для Цели 2 (требования §6). По координатам из профиля."""

    async def current(self, lat: float, lon: float) -> dict:
        ...


class EmbeddingProvider(Protocol):
    """Текстовые эмбеддинги — для поиска дублей вещей (требования §5, pgvector)."""

    async def embed(self, text: str) -> list[float]:
        ...


class TrendProvider(Protocol):
    """Актуальные тренды — чтобы лук был современным.

    Возвращает короткую сводку трендов под заданный контекст (сезон/пол/стиль).
    Реализация может ходить в веб (web_search). Результат кэшируется выше.
    """

    async def current_brief(self, context: str) -> str:
        ...


class StorageProvider(Protocol):
    """Хранилище блобов фото. Метаданные лежат в БД (раздел 10.1).

    ``delete_prefix`` нужен для команды «удалить все данные пользователя».
    """

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        ...

    async def delete_prefix(self, prefix: str) -> int:
        ...
