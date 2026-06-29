"""Адаптер эмбеддингов на Voyage AI. Реализует EmbeddingProvider.

Voyage-клиент синхронный — оборачиваем в ``asyncio.to_thread``.
"""
from __future__ import annotations

import asyncio

import voyageai


class VoyageEmbedder:
    def __init__(self, api_key: str, model: str = "voyage-3") -> None:
        self._client = voyageai.Client(api_key=api_key)
        self._model = model

    async def embed(self, text: str) -> list[float]:
        result = await asyncio.to_thread(
            self._client.embed, [text], model=self._model, input_type="document"
        )
        return list(result.embeddings[0])
