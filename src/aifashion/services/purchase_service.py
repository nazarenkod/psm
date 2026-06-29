"""Оркестрация Цели 1 «Купить ли вещь» (требования §5).

Собирает контекст (профиль, гардероб, найденные дубли по эмбеддингу) и зовёт
движок. Вынесено в сервис, чтобы логика была покрыта тестами, а хендлер — тонким.
"""
from __future__ import annotations

from aifashion.core.models import ImageInput, PurchaseVerdict
from aifashion.engine.goal1_purchase import PurchaseAdvisor
from aifashion.services.profile_service import ProfileService
from aifashion.services.wardrobe_service import WardrobeService


class PurchaseService:
    def __init__(
        self,
        profile: ProfileService,
        wardrobe: WardrobeService,
        advisor: PurchaseAdvisor,
    ) -> None:
        self._profile = profile
        self._wardrobe = wardrobe
        self._advisor = advisor

    async def evaluate(
        self,
        user_id: int,
        *,
        image: ImageInput | None = None,
        item_link: str | None = None,
        note: str | None = None,
    ) -> PurchaseVerdict:
        profile = await self._profile.get_or_create(user_id)
        wardrobe = await self._wardrobe.summary_for_prompt(user_id)

        duplicates = []
        if image is not None:
            # Распознаём вещь и ищем похожее в гардеробе (§5).
            attrs = await self._wardrobe.extract_attrs(image)
            duplicates = await self._wardrobe.find_duplicates(user_id, attrs)

        return await self._advisor.evaluate(
            profile=profile,
            wardrobe=wardrobe,
            duplicates=duplicates,
            images=[image] if image else None,
            item_link=item_link,
            note=note,
        )
