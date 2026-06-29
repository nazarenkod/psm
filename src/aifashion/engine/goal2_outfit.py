"""Цель 2 — «Что надеть сейчас» (требования §6).

Образ собирается ИЗ ИМЕЮЩИХСЯ вещей (модель выбирает их id). Учитывает погоду,
повод/формальность, что давно не носилось, предпочтения и АКТУАЛЬНЫЕ ТРЕНДЫ —
но тренды как ориентир, не в ущерб тому, что идёт пользователю и практичности (§8).
"""
from __future__ import annotations

from aifashion.core.models import (
    OutfitSuggestion,
    UserProfile,
    WardrobeItem,
)
from aifashion.engine.goal1_purchase import summarize_profile
from aifashion.providers.base import LLMProvider

SYSTEM_PROMPT = (
    "Ты — персональный стилист. Собери КОНКРЕТНЫЙ образ на сегодня из вещей, которые "
    "уже есть у пользователя (выбирай их по id из списка).\n"
    "Учитывай: погоду, повод и уровень формальности, что давно не носилось "
    "(освежай ротацию), предпочтения и внешность пользователя.\n"
    "Тренды — это ОРИЕНТИР для актуальности, но не в ущерб тому, что идёт пользователю, "
    "и практичности. Честность и практичность важнее моды.\n"
    "Если для идеального образа чего-то не хватает в гардеробе — кратко отметь это в "
    "поле missing (зацепка к плану докупок), но образ собери из того, что есть.\n"
    "Отвечай на языке пользователя. Верни id выбранных вещей и понятное пояснение."
)


def format_weather(weather: dict | None) -> str:
    if not weather:
        return "Погода неизвестна."
    t = weather.get("temperature_2m")
    feels = weather.get("apparent_temperature")
    wind = weather.get("wind_speed_10m")
    bits = []
    if t is not None:
        bits.append(f"{t}°C")
    if feels is not None:
        bits.append(f"ощущается как {feels}°C")
    if wind is not None:
        bits.append(f"ветер {wind} м/с")
    return "Погода: " + ", ".join(bits) if bits else "Погода неизвестна."


def summarize_wardrobe_for_outfit(items: list[WardrobeItem]) -> str:
    if not items:
        return "Гардероб пуст — образ собрать не из чего."
    lines = []
    for it in items:
        a = it.attrs
        parts = [a.category] + [x for x in (a.color, a.style, a.brand) if x]
        tail = " (давно не носилось)" if it.last_seen_at is None else ""
        lines.append(f"[{it.id}] " + ", ".join(parts) + tail)
    return "Гардероб (выбирай по id):\n" + "\n".join(lines)


def build_prompt(
    profile: UserProfile | None,
    items: list[WardrobeItem],
    *,
    occasion: str | None,
    weather: dict | None,
    trend_brief: str | None,
) -> str:
    parts = [
        summarize_profile(profile),
        format_weather(weather),
        f"Повод: {occasion}" if occasion else "Повод: повседневный.",
        summarize_wardrobe_for_outfit(items),
    ]
    if trend_brief:
        parts.append("Актуальные тренды (ориентир, не в ущерб тому, что идёт):\n" + trend_brief)
    parts.append("Собери образ из вещей выше и верни их id с пояснением.")
    return "\n\n".join(parts)


def format_outfit(suggestion: OutfitSuggestion, items_by_id: dict[int, WardrobeItem]) -> str:
    lines = ["👗 Образ на сегодня:"]
    for iid in suggestion.item_ids:
        it = items_by_id.get(iid)
        if it is None:
            continue
        a = it.attrs
        parts = [a.category] + [x for x in (a.color, a.style) if x]
        lines.append("• " + ", ".join(parts))
    lines += ["", suggestion.explanation]
    if suggestion.missing:
        lines += ["", f"Не хватает до идеала: {suggestion.missing}"]
    return "\n".join(lines)


class OutfitAdvisor:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def suggest(
        self,
        *,
        profile: UserProfile | None,
        wardrobe: list[WardrobeItem],
        occasion: str | None = None,
        weather: dict | None = None,
        trend_brief: str | None = None,
    ) -> OutfitSuggestion:
        prompt = build_prompt(
            profile, wardrobe, occasion=occasion, weather=weather, trend_brief=trend_brief
        )
        return await self._llm.parse(
            system=SYSTEM_PROMPT, prompt=prompt, schema=OutfitSuggestion
        )
