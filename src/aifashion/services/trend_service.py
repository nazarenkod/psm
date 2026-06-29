"""Сервис трендов: сводка актуальной моды с кэшем по TTL.

Тренды меняются медленно — кэшируем, чтобы не дёргать модель/веб на каждый запрос
(экономия §15). Если провайдер не настроен — возвращаем None (лук строится без
трендового слоя, мягкая деградация).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aifashion.core.ports import TrendCacheRepository
from aifashion.providers.base import TrendProvider


class TrendService:
    def __init__(
        self,
        provider: TrendProvider | None,
        cache: TrendCacheRepository,
        *,
        ttl_days: int = 7,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._ttl = timedelta(days=ttl_days)

    async def brief(self, context: str) -> str | None:
        if self._provider is None:
            return None
        cached = await self._cache.get(context)
        if cached is not None:
            text, updated_at = cached
            if datetime.now(timezone.utc) - updated_at < self._ttl:
                return text
        text = await self._provider.current_brief(context)
        await self._cache.set(context, text)
        return text
