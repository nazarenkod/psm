"""Цель 1 — «Купить ли эту вещь» (требования §5). Ядро продукта.

Принцип §2: вердикт независим, партнёрские интересы на него не влияют. Поэтому
в этом модуле НЕТ ничего про «где купить» / партнёрку — только оценка полезности.
"""
from __future__ import annotations

from aifashion.core.models import (
    ConversationTurn,
    ImageInput,
    PurchaseVerdict,
    UserProfile,
    WardrobeItem,
)
from aifashion.providers.base import LLMProvider

SYSTEM_PROMPT = (
    "Ты — честный персональный стилист. Твоя задача — решить, стоит ли пользователю "
    "покупать конкретную вещь, исходя ТОЛЬКО из его пользы.\n"
    "Жёсткие правила:\n"
    "- Честность: не подстраивайся под желаемый ответ. Если не стоит брать — так и скажи.\n"
    "- Тактичность: усиливай достоинства, не унижай.\n"
    "- Обоснование обязательно: объясняй ПОЧЕМУ, а не только балл.\n"
    "- Никаких рекламных/партнёрских соображений: вопрос «где купить выгоднее» тебя "
    "не касается. Решай только полезность вещи.\n"
    "- Отвечай на языке пользователя.\n"
    "Оцени: сочетаемость с гардеробом, полезность (сколько новых образов добавит), "
    "уникальность (нет ли дубля), соответствие стилю и внешности, оправданность цены. "
    "Если цена неизвестна — оцени приблизительно и отметь это."
)


def summarize_wardrobe(items: list[WardrobeItem]) -> str:
    """Компактная сводка гардероба для промпта (экономия токенов, §15).

    Работает на неполном гардеробе (§4.3): если пусто — честно сообщаем модели.
    """
    if not items:
        return "Гардероб пока пуст или почти пуст — учитывай это: оценивай вещь как базу."
    lines = []
    for it in items:
        a = it.attrs
        parts = [a.category]
        if a.color:
            parts.append(a.color)
        if a.style:
            parts.append(a.style)
        if a.brand:
            parts.append(a.brand)
        lines.append("- " + ", ".join(parts))
    return "Гардероб пользователя:\n" + "\n".join(lines)


def summarize_profile(profile: UserProfile | None) -> str:
    if profile is None:
        return "Профиль пользователя ещё не заполнен."
    p = profile
    bits: list[str] = []
    if p.sex:
        bits.append(f"пол: {p.sex}")
    if p.age:
        bits.append(f"возраст: {p.age}")
    if p.color_type:
        bits.append(f"цветотип: {p.color_type}")
    if p.contrast:
        bits.append(f"контрастность: {p.contrast}")
    if p.lifestyle:
        bits.append(f"образ жизни: {p.lifestyle}")
    if p.dress_code:
        bits.append(f"дресс-код: {p.dress_code}")
    if p.silhouette and p.silhouette.recommendations:
        bits.append("силуэт: " + "; ".join(p.silhouette.recommendations))
    return "Профиль: " + (", ".join(bits) if bits else "почти пуст") + "."


def summarize_duplicates(duplicates: list[WardrobeItem]) -> str | None:
    """Похожие вещи из гардероба (найдены по эмбеддингу, §5) — для оценки уникальности."""
    if not duplicates:
        return None
    lines = []
    for it in duplicates:
        a = it.attrs
        parts = [a.category] + [x for x in (a.color, a.style, a.brand) if x]
        lines.append("- " + ", ".join(parts))
    return (
        "В гардеробе уже есть похожие вещи (учти при оценке уникальности — нет ли дубля):\n"
        + "\n".join(lines)
    )


def build_prompt(
    profile: UserProfile | None,
    items: list[WardrobeItem],
    *,
    duplicates: list[WardrobeItem] | None = None,
    item_link: str | None = None,
    note: str | None = None,
) -> str:
    parts = [summarize_profile(profile), summarize_wardrobe(items)]
    dup = summarize_duplicates(duplicates or [])
    if dup:
        parts.append(dup)
    if item_link:
        parts.append(f"Ссылка на вещь: {item_link}")
    if note:
        parts.append(f"Комментарий пользователя: {note}")
    parts.append(
        "Оцени вещь (на фото и/или по ссылке) и верни вердикт с баллом и обоснованием."
    )
    return "\n\n".join(parts)


def format_verdict(v: PurchaseVerdict) -> str:
    """Человеческое представление вердикта для Telegram."""
    head = "✅ Бери" if v.buy else "🚫 Не бери"
    lines = [f"{head} · {v.score}/100", "", v.reasoning]
    extras = [
        ("Сочетаемость", v.compatibility),
        ("Польза", v.usefulness),
        ("Уникальность", v.uniqueness),
        ("Тебе идёт", v.fit_to_user),
        ("Цена", v.price_justified),
    ]
    detail = [f"• {label}: {text}" for label, text in extras if text]
    if detail:
        lines += ["", *detail]
    return "\n".join(lines)


class PurchaseAdvisor:
    """Движок Цели 1. Зависит только от абстрактного LLMProvider."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def evaluate(
        self,
        *,
        profile: UserProfile | None,
        wardrobe: list[WardrobeItem],
        duplicates: list[WardrobeItem] | None = None,
        images: list[ImageInput] | None = None,
        item_link: str | None = None,
        note: str | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> PurchaseVerdict:
        prompt = build_prompt(
            profile, wardrobe, duplicates=duplicates, item_link=item_link, note=note
        )
        return await self._llm.parse(
            system=SYSTEM_PROMPT,
            prompt=prompt,
            schema=PurchaseVerdict,
            images=images,
            history=history,
        )
