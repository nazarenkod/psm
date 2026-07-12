"""Адаптер генерации изображений на OpenAI (gpt-image-1). Реализует ImageGenProvider.

Claude не генерирует картинки, поэтому для визуализации капсул идём через OpenAI.
Рассуждения (что за капсула, какой промпт) остаются на Claude — сюда приходит
готовый визуальный промпт.
"""
from __future__ import annotations

import base64

from openai import AsyncOpenAI


class OpenAIImageGen:
    def __init__(self, api_key: str, model: str = "gpt-image-1") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate(self, prompt: str, *, size: str = "1024x1024") -> bytes:
        resp = await self._client.images.generate(
            model=self._model, prompt=prompt, size=size, n=1
        )
        return base64.b64decode(resp.data[0].b64_json)
