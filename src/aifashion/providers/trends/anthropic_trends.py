"""Адаптер анализа трендов на Claude + web_search. Реализует TrendProvider.

Свежесть берём из веба; результат кэшируется в TrendService (тренды меняются
медленно — незачем дёргать на каждый запрос, экономия §15).
"""
from __future__ import annotations

from anthropic import AsyncAnthropic

_SYSTEM = (
    "Ты следишь за модой. Дай КОРОТКУЮ сводку актуальных трендов (3–6 пунктов) "
    "строго под указанный контекст (сезон, пол, стиль). Только то, что реально "
    "носят сейчас, без воды и без рекламы конкретных брендов."
)


class AnthropicTrendProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def current_brief(self, context: str) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=800,
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Контекст: {context}. Какие сейчас актуальные тренды? "
                        "Сверься с вебом для свежести."
                    ),
                }
            ],
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()
