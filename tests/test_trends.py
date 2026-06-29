import pytest

from aifashion.services.trend_service import TrendService
from tests.fakes import FakeTrendCache, FakeTrendProvider


@pytest.mark.asyncio
async def test_brief_caches_within_ttl():
    provider = FakeTrendProvider("оверсайз")
    svc = TrendService(provider, FakeTrendCache(), ttl_days=7)

    first = await svc.brief("осень, ж")
    second = await svc.brief("осень, ж")

    assert first == second == "оверсайз"
    assert len(provider.calls) == 1  # второй раз взяли из кэша, модель не дёргали


@pytest.mark.asyncio
async def test_brief_refetches_after_ttl():
    from datetime import datetime, timedelta, timezone

    provider = FakeTrendProvider("новое")
    cache = FakeTrendCache()
    cache.store["осень, ж"] = ("старое", datetime.now(timezone.utc) - timedelta(days=30))
    svc = TrendService(provider, cache, ttl_days=7)

    result = await svc.brief("осень, ж")

    assert result == "новое"        # протухло → перезапросили
    assert provider.calls == ["осень, ж"]


@pytest.mark.asyncio
async def test_no_provider_returns_none():
    svc = TrendService(None, FakeTrendCache())
    assert await svc.brief("любой контекст") is None
