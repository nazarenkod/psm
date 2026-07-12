"""Адаптер LLM/Vision на Anthropic SDK (Claude).

Единственное место, знающее про Anthropic. Реализует LLMProvider. Использует
structured outputs (надёжный вердикт по схеме) и adaptive thinking.
"""
from __future__ import annotations

from typing import TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from aifashion.core.models import ConversationTurn, ImageInput

TModel = TypeVar("TModel", bound=BaseModel)


class AnthropicProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    def _content(self, prompt: str, images: list[ImageInput] | None) -> list[dict]:
        blocks: list[dict] = []
        for img in images or []:
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.media_type,
                        "data": img.data_b64,
                    },
                }
            )
        blocks.append({"type": "text", "text": prompt})
        return blocks

    def _messages(
        self,
        prompt: str,
        images: list[ImageInput] | None,
        history: list[ConversationTurn] | None,
    ) -> list[dict]:
        msgs: list[dict] = [{"role": t.role, "content": t.text} for t in history or []]
        msgs.append({"role": "user", "content": self._content(prompt, images)})
        return msgs

    async def parse(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[TModel],
        images: list[ImageInput] | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> TModel:
        resp = await self._client.messages.parse(
            model=self._model,
            max_tokens=4096,
            system=system,
            thinking={"type": "adaptive"},
            messages=self._messages(prompt, images, history),
            output_format=schema,
        )
        if resp.parsed_output is None:
            raise RuntimeError(f"Не удалось получить структурированный ответ: {resp.stop_reason}")
        return resp.parsed_output

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        images: list[ImageInput] | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            thinking={"type": "adaptive"},
            messages=self._messages(prompt, images, history),
        )
        return "".join(b.text for b in resp.content if b.type == "text")
