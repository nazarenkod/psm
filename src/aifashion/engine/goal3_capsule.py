"""Цель 3 — «Капсула и что докупить» (требования §7).

Определяет пробелы, строит ПОСЛЕДОВАТЕЛЬНОСТЬ покупок (приоритетная следующая
вещь, а не список из 20), объясняет как капсула работает. В том же структурном
ответе модель отдаёт визуальный промпт для генератора изображений (иллюстративно).

Партнёрка («где взять выгоднее») подключается на реактивном шаге отдельно —
здесь только решение о полезности (принцип §2).
"""
from __future__ import annotations

from aifashion.core.models import CapsulePlan, ConversationTurn, UserProfile, WardrobeItem
from aifashion.engine.goal1_purchase import summarize_profile, summarize_wardrobe
from aifashion.providers.base import LLMProvider

SYSTEM_PROMPT = (
    "Ты — персональный стилист, строишь капсульный гардероб. По профилю, образу "
    "жизни и текущему гардеробу:\n"
    "1) определи пробелы относительно образа жизни и стиля (gaps);\n"
    "2) назови ОДНУ приоритетную следующую покупку (next_purchase) — самую полезную "
    "сейчас, а не список из 20;\n"
    "3) объясни, как капсула будет работать (explanation);\n"
    "4) составь image_prompt — подробное визуальное описание концепта капсулы для "
    "генератора изображений: аккуратная раскладка/лукбук на нейтральном фоне, палитра "
    "под внешность пользователя, без текста и логотипов на картинке.\n"
    "Тренды учитывай как ориентир, не в ущерб практичности и тому, что идёт. "
    "Отвечай на языке пользователя."
)


def build_prompt(
    profile: UserProfile | None,
    wardrobe: list[WardrobeItem],
    *,
    trend_brief: str | None = None,
) -> str:
    parts = [summarize_profile(profile), summarize_wardrobe(wardrobe)]
    if trend_brief:
        parts.append("Актуальные тренды (ориентир):\n" + trend_brief)
    parts.append(
        "Построй капсулу: пробелы, приоритетная следующая покупка, как это работает, "
        "и визуальный промпт для изображения."
    )
    return "\n\n".join(parts)


def format_capsule(plan: CapsulePlan) -> str:
    lines = ["🧩 Капсула и план докупок", ""]
    if plan.gaps:
        lines.append("Пробелы:")
        lines += [f"• {g}" for g in plan.gaps]
        lines.append("")
    lines.append(f"👉 Следующая покупка: {plan.next_purchase}")
    lines += ["", plan.explanation]
    return "\n".join(lines)


class CapsuleAdvisor:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def plan(
        self,
        *,
        profile: UserProfile | None,
        wardrobe: list[WardrobeItem],
        trend_brief: str | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> CapsulePlan:
        prompt = build_prompt(profile, wardrobe, trend_brief=trend_brief)
        return await self._llm.parse(
            system=SYSTEM_PROMPT, prompt=prompt, schema=CapsulePlan, history=history
        )
