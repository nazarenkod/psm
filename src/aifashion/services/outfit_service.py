"""Оркестрация Цели 2 «Что надеть сейчас» (требования §6).

Собирает погоду (по координатам профиля), гардероб и трендовый слой, зовёт движок,
подтверждает носибельность выбранных вещей (§4.4). Вынесено в сервис для тестов.
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog

from aifashion.core.models import OutfitSuggestion, UserProfile, WardrobeItem
from aifashion.engine.goal2_outfit import OutfitAdvisor, format_outfit
from aifashion.providers.base import WeatherProvider
from aifashion.services.conversation_service import ConversationService
from aifashion.services.profile_service import ProfileService
from aifashion.services.trend_service import TrendService
from aifashion.services.wardrobe_service import WardrobeService

log = structlog.get_logger()

_SEASONS = {12: "зима", 1: "зима", 2: "зима", 3: "весна", 4: "весна", 5: "весна",
            6: "лето", 7: "лето", 8: "лето", 9: "осень", 10: "осень", 11: "осень"}


class NeedLocation(Exception):
    """Нет координат в профиле — бот должен запросить геолокацию (§6)."""


def _season(month: int) -> str:
    return _SEASONS.get(month, "")


class OutfitService:
    def __init__(
        self,
        profile: ProfileService,
        wardrobe: WardrobeService,
        weather: WeatherProvider,
        trends: TrendService,
        advisor: OutfitAdvisor,
        conversation: ConversationService,
    ) -> None:
        self._profile = profile
        self._wardrobe = wardrobe
        self._weather = weather
        self._trends = trends
        self._advisor = advisor
        self._conversation = conversation

    def _trend_context(self, profile: UserProfile, occasion: str | None, month: int) -> str:
        sex = profile.sex or "унисекс"
        season = _season(month)
        occ = occasion or "повседневный"
        return f"{season}, {sex}, повод: {occ}"

    async def suggest(
        self, user_id: int, *, occasion: str | None = None
    ) -> tuple[OutfitSuggestion, dict[int, WardrobeItem]]:
        profile = await self._profile.get_or_create(user_id)
        if profile.lat is None or profile.lon is None:
            raise NeedLocation

        weather = await self._weather.current(profile.lat, profile.lon)
        items = await self._wardrobe.summary_for_prompt(user_id)
        context = self._trend_context(profile, occasion, datetime.now(timezone.utc).month)
        trend_brief = await self._trends.brief(context)
        history = await self._conversation.history(user_id)

        suggestion = await self._advisor.suggest(
            profile=profile,
            wardrobe=items,
            occasion=occasion,
            weather=weather,
            trend_brief=trend_brief,
            history=history,
        )

        by_id = {it.id: it for it in items}
        # Вещи появились в образе → подтверждаем носибельность (§4.4).
        for iid in suggestion.item_ids:
            if iid in by_id:
                await self._wardrobe.confirm_worn(iid)

        await self._conversation.record_user(user_id, f"Что надеть, повод: {occasion or 'обычный'}")
        await self._conversation.record_assistant(user_id, format_outfit(suggestion, by_id))
        log.info(
            "goal2.outfit",
            user_id=user_id,
            occasion=occasion,
            items=len(suggestion.item_ids),
            wardrobe=len(items),
            trend=trend_brief is not None,
        )
        return suggestion, by_id
