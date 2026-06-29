"""Сервис профиля (требования §4.1, §4.2, §10).

Критический инвариант (§4.2): профиль внешности/силуэта обучается ТОЛЬКО на
selfie. ``learn_appearance_from_selfie`` — единственная точка, где внешность
обновляется, и она принимает только selfie.
"""
from __future__ import annotations

from aifashion.core.models import (
    AppearanceAnalysis,
    ImageInput,
    PhotoRole,
    UserProfile,
)
from aifashion.core.ports import UserRepository
from aifashion.providers.base import LLMProvider, StorageProvider

_APPEARANCE = (
    "Определи по фото лица при дневном свете: цветотип, уровень контрастности и "
    "КАЧЕСТВЕННЫЙ силуэтный портрет (телосложение, пропорции на глаз) с конкретными "
    "рекомендациями вида «удлиняй низ». НЕ давай измерений в сантиметрах и НЕ "
    "присваивай жёстких ярлыков типа фигуры как факт."
)


class ProfileService:
    def __init__(
        self,
        repo: UserRepository,
        llm: LLMProvider,
        storage: StorageProvider,
    ) -> None:
        self._repo = repo
        self._llm = llm
        self._storage = storage

    async def get_or_create(self, telegram_id: int, language: str | None = None) -> UserProfile:
        return await self._repo.get_or_create(telegram_id, language)

    async def learn_appearance_from_selfie(
        self, user_id: int, image: ImageInput, role: PhotoRole
    ) -> UserProfile:
        """Обновить внешность профиля. ТОЛЬКО для selfie (§4.2)."""
        if role is not PhotoRole.selfie:
            raise ValueError(
                "Профиль внешности учится только на selfie — "
                f"получена роль {role.value}"
            )
        analysis = await self._llm.parse(
            system=_APPEARANCE,
            prompt="Проанализируй внешность пользователя на фото.",
            schema=AppearanceAnalysis,
            images=[image],
        )
        profile = await self._repo.get_or_create(user_id)
        profile.color_type = analysis.color_type or profile.color_type
        profile.contrast = analysis.contrast or profile.contrast
        profile.silhouette = analysis.silhouette or profile.silhouette
        return await self._repo.save(profile)

    async def set_location(self, user_id: int, lat: float, lon: float) -> None:
        await self._repo.set_location(user_id, lat, lon)

    async def delete_everything(self, user_id: int) -> list[str]:
        """`/delete` — стереть все данные пользователя (§10). Вернуть ключи блобов."""
        return await self._repo.delete_all(user_id)
