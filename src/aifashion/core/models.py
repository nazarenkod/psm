"""Доменные типы — общий язык между ботом, провайдерами, сервисами и движком.

Эти типы НЕ зависят ни от конкретного LLM-провайдера, ни от ORM.
Делятся на:
  * value-объекты (что извлекаем/возвращаем);
  * сущности (что персистим) — с id и привязкой к user_id.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Перечисления ────────────────────────────────────────────────────────────


class PhotoRole(str, Enum):
    """Дисциплина источников фото (требования §4.2) — жёсткое требование.

    Профиль внешности/силуэта обучается ТОЛЬКО на ``selfie``.
    """

    selfie = "selfie"                       # сам пользователь — можно учить профиль
    outfit_reference = "outfit_reference"   # чужой образ — только стиль и вещи
    product_shot = "product_shot"           # карточка товара — только вещь
    flat_lay = "flat_lay"                   # вещь без человека — только вещь
    unknown = "unknown"                     # неоднозначно → бот обязан спросить


class ItemStatus(str, Enum):
    """Жизненный цикл вещи (требования §4.4)."""

    active = "active"        # носится
    archived = "archived"    # больше не носится
    candidate = "candidate"  # распознана, но не подтверждена пользователем


# ── Value-объекты ───────────────────────────────────────────────────────────


class ImageInput(BaseModel):
    """Изображение для передачи в мультимодальную модель."""

    media_type: str = "image/jpeg"
    data_b64: str


class WardrobeItemAttrs(BaseModel):
    """Характеристики вещи, извлекаемые vision-моделью (требования §4.3)."""

    category: str
    color: str | None = None
    material: str | None = None
    seasonality: str | None = None
    style: str | None = None
    brand: str | None = None
    price: float | None = None


class SilhouetteHints(BaseModel):
    """Качественный портрет силуэта (требования §4.1) — без сантиметров и ярлыков."""

    build: str | None = None        # худощавое / среднее / плотное
    proportions: str | None = None  # на глаз: ноги/торс, плечи
    recommendations: list[str] = Field(default_factory=list)  # «удлиняй низ» и т.п.


class PurchaseVerdict(BaseModel):
    """Выход Цели 1 «Купить ли эту вещь» (требования §5).

    Обязательно объяснение *почему*, а не только число.
    Партнёрские интересы на этот вердикт не влияют (требования §2).
    """

    buy: bool
    score: int = Field(ge=0, le=100)
    reasoning: str
    compatibility: str | None = None    # сочетаемость с гардеробом
    usefulness: str | None = None       # сколько новых образов добавит
    uniqueness: str | None = None       # нет ли дубля
    fit_to_user: str | None = None      # стиль + внешность
    price_justified: str | None = None  # оправданность цены


class PhotoClassification(BaseModel):
    """Результат role-tagging: роль + уверенность (требования §4.2)."""

    role: PhotoRole
    confident: bool  # если False — бот обязан спросить, а не угадывать


class ExtractedItems(BaseModel):
    """Вещи, извлечённые при разборе лука (требования §4.3)."""

    items: list[WardrobeItemAttrs] = Field(default_factory=list)


class AppearanceAnalysis(BaseModel):
    """Анализ внешности по selfie (требования §4.1). Учим профиль ТОЛЬКО отсюда."""

    color_type: str | None = None
    contrast: str | None = None
    silhouette: SilhouetteHints | None = None


# ── Сущности (персистятся, привязаны к user_id) ─────────────────────────────


class UserProfile(BaseModel):
    """Профиль пользователя (требования §4.1). Привязан к Telegram ID."""

    id: int                          # = Telegram ID (идентификация без регистрации)
    language: str | None = None      # для подстройки языка вердиктов (§8)
    color_type: str | None = None
    contrast: str | None = None
    silhouette: SilhouetteHints | None = None
    sex: str | None = None
    age: int | None = None
    height_cm: int | None = None
    lifestyle: str | None = None
    dress_code: str | None = None
    lat: float | None = None         # координаты для погоды (§6)
    lon: float | None = None


class WardrobeItem(BaseModel):
    """Вещь гардероба (требования §4.3, §4.4)."""

    id: int
    user_id: int
    attrs: WardrobeItemAttrs
    status: ItemStatus = ItemStatus.active
    photo_key: str | None = None         # ключ каноничного фото в хранилище
    last_seen_at: datetime | None = None
