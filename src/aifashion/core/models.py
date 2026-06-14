"""Доменные типы (Pydantic) — общий язык между ботом, провайдерами и движком.

Эти типы НЕ зависят ни от конкретного LLM-провайдера, ни от ORM.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PhotoRole(str, Enum):
    """Дисциплина источников фото (раздел 4.2) — жёсткое требование.

    Профиль внешности/силуэта обучается ТОЛЬКО на ``selfie``.
    """

    selfie = "selfie"            # сам пользователь — можно учить профиль
    outfit_reference = "outfit_reference"  # чужой образ — только стиль и вещи
    product_shot = "product_shot"          # карточка товара — только вещь
    flat_lay = "flat_lay"                  # вещь без человека — только вещь
    unknown = "unknown"          # неоднозначно → бот обязан спросить


class ImageInput(BaseModel):
    """Изображение для передачи в мультимодальную модель."""

    media_type: str = "image/jpeg"
    data_b64: str


class WardrobeItemAttrs(BaseModel):
    """Характеристики вещи, извлекаемые vision-моделью (раздел 4.3)."""

    category: str
    color: str | None = None
    material: str | None = None
    seasonality: str | None = None
    style: str | None = None
    brand: str | None = None
    price: float | None = None


class SilhouetteHints(BaseModel):
    """Качественный портрет силуэта (раздел 4.1) — без сантиметров и ярлыков."""

    build: str | None = None        # худощавое / среднее / плотное
    proportions: str | None = None  # на глаз: ноги/торс, плечи
    recommendations: list[str] = Field(default_factory=list)  # «удлиняй низ» и т.п.


class PurchaseVerdict(BaseModel):
    """Выход Цели 1 «Купить ли эту вещь» (раздел 5).

    Обязательно объяснение *почему*, а не только число.
    Партнёрские интересы на этот вердикт не влияют (раздел 2).
    """

    buy: bool
    score: int = Field(ge=0, le=100)
    reasoning: str
    compatibility: str | None = None   # сочетаемость с гардеробом
    usefulness: str | None = None      # сколько новых образов добавит
    uniqueness: str | None = None      # нет ли дубля
    fit_to_user: str | None = None     # стиль + внешность
    price_justified: str | None = None # оправданность цены
