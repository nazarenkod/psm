"""Оркестрация Цели 3 «Капсула» (требования §7) + генерация изображения.

Claude строит план и визуальный промпт; OpenAI по промпту рисует концепт капсулы
(если генератор настроен — иначе капсула отдаётся текстом, мягкая деградация).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

from aifashion.core.models import CapsulePlan
from aifashion.engine.goal3_capsule import CapsuleAdvisor, format_capsule
from aifashion.providers.base import ImageGenProvider, StorageProvider
from aifashion.services.conversation_service import ConversationService
from aifashion.services.profile_service import ProfileService
from aifashion.services.trend_service import TrendService
from aifashion.services.wardrobe_service import WardrobeService

log = structlog.get_logger()

_SEASONS = {12: "зима", 1: "зима", 2: "зима", 3: "весна", 4: "весна", 5: "весна",
            6: "лето", 7: "лето", 8: "лето", 9: "осень", 10: "осень", 11: "осень"}


@dataclass
class CapsuleResult:
    plan: CapsulePlan
    image: bytes | None = None  # None — если генератор не настроен


class CapsuleService:
    def __init__(
        self,
        profile: ProfileService,
        wardrobe: WardrobeService,
        trends: TrendService,
        advisor: CapsuleAdvisor,
        conversation: ConversationService,
        *,
        image_gen: ImageGenProvider | None = None,
        storage: StorageProvider | None = None,
        image_size: str = "1024x1024",
    ) -> None:
        self._profile = profile
        self._wardrobe = wardrobe
        self._trends = trends
        self._advisor = advisor
        self._conversation = conversation
        self._image_gen = image_gen
        self._storage = storage
        self._image_size = image_size

    async def build(self, user_id: int) -> CapsuleResult:
        profile = await self._profile.get_or_create(user_id)
        wardrobe = await self._wardrobe.summary_for_prompt(user_id)
        season = _SEASONS.get(datetime.now(timezone.utc).month, "")
        trend_brief = await self._trends.brief(f"{season}, {profile.sex or 'унисекс'}, капсула")
        history = await self._conversation.history(user_id)

        plan = await self._advisor.plan(
            profile=profile, wardrobe=wardrobe, trend_brief=trend_brief, history=history
        )

        image: bytes | None = None
        if self._image_gen is not None:
            image = await self._image_gen.generate(plan.image_prompt, size=self._image_size)
            if self._storage is not None:
                key = f"users/{user_id}/capsule/{uuid.uuid4().hex}"
                await self._storage.put(key, image, "image/png")

        await self._conversation.record_user(user_id, "Собери капсулу и план докупок.")
        await self._conversation.record_assistant(user_id, format_capsule(plan))
        log.info(
            "goal3.capsule",
            user_id=user_id,
            next_purchase=plan.next_purchase,
            gaps=len(plan.gaps),
            image=image is not None,
        )
        return CapsuleResult(plan=plan, image=image)
