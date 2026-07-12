"""Оркестрация Цели 1 «Купить ли вещь» (требования §5).

Собирает контекст (профиль, гардероб, найденные дубли по эмбеддингу, историю
общения) и зовёт движок. Записывает диалог в память агента.
"""
from __future__ import annotations

from aifashion.core.models import ImageInput, PurchaseVerdict
from aifashion.engine.goal1_purchase import PurchaseAdvisor, format_verdict
from aifashion.services.conversation_service import ConversationService
from aifashion.services.profile_service import ProfileService
from aifashion.services.wardrobe_service import WardrobeService


class PurchaseService:
    def __init__(
        self,
        profile: ProfileService,
        wardrobe: WardrobeService,
        advisor: PurchaseAdvisor,
        conversation: ConversationService,
    ) -> None:
        self._profile = profile
        self._wardrobe = wardrobe
        self._advisor = advisor
        self._conversation = conversation

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
        history = await self._conversation.history(user_id)

        duplicates = []
        if image is not None:
            # Распознаём вещь и ищем похожее в гардеробе (§5).
            attrs = await self._wardrobe.extract_attrs(image)
            duplicates = await self._wardrobe.find_duplicates(user_id, attrs)

        verdict = await self._advisor.evaluate(
            profile=profile,
            wardrobe=wardrobe,
            duplicates=duplicates,
            images=[image] if image else None,
            item_link=item_link,
            note=note,
            history=history,
        )

        request = item_link or note or "[фото вещи к покупке]"
        await self._conversation.record_user(user_id, f"Оценка покупки: {request}")
        await self._conversation.record_assistant(user_id, format_verdict(verdict))
        return verdict
