import pytest

from aifashion.core.models import OutfitSuggestion, UserProfile, WardrobeItem
from aifashion.engine.goal2_outfit import (
    SYSTEM_PROMPT,
    OutfitAdvisor,
    build_prompt,
    format_outfit,
    format_weather,
    summarize_wardrobe_for_outfit,
)
from aifashion.services.outfit_service import NeedLocation, OutfitService
from aifashion.services.profile_service import ProfileService
from aifashion.services.trend_service import TrendService
from aifashion.services.wardrobe_service import WardrobeService
from tests.fakes import (
    FakeLLM,
    FakeStorage,
    FakeTrendCache,
    FakeTrendProvider,
    FakeUserRepo,
    FakeWardrobeRepo,
    FakeWeather,
    attrs,
)


def _item(iid, cat, last_seen=None, **kw):
    return WardrobeItem(id=iid, user_id=1, attrs=attrs(cat, **kw), last_seen_at=last_seen)


# ── Движок ──────────────────────────────────────────────────────────────────


def test_format_weather():
    assert "12°C" in format_weather({"temperature_2m": 12})
    assert "неизвест" in format_weather(None).lower()


def test_wardrobe_lists_ids_and_marks_unworn():
    text = summarize_wardrobe_for_outfit([_item(1, "coat"), _item(2, "jeans")])
    assert "[1]" in text and "[2]" in text
    assert "давно не носилось" in text  # last_seen None → подсветка ротации


def test_build_prompt_has_weather_occasion_and_trend():
    prompt = build_prompt(
        UserProfile(id=1),
        [_item(1, "coat")],
        occasion="свидание",
        weather={"temperature_2m": 5},
        trend_brief="оверсайз",
    )
    assert "свидание" in prompt
    assert "5°C" in prompt
    assert "оверсайз" in prompt
    assert "[1]" in prompt


def test_system_prompt_keeps_trends_subordinate_to_fit():
    # Тренды — ориентир, не в ущерб тому, что идёт пользователю (§8)
    low = SYSTEM_PROMPT.lower()
    assert "тренд" in low and "не в ущерб" in low


def test_format_outfit_lists_items_and_missing():
    items = {1: _item(1, "coat", color="beige"), 2: _item(2, "boots")}
    s = OutfitSuggestion(item_ids=[1, 2], explanation="тепло и по поводу", missing="ремень")
    out = format_outfit(s, items)
    assert "coat" in out and "boots" in out
    assert "тепло и по поводу" in out
    assert "ремень" in out


@pytest.mark.asyncio
async def test_advisor_returns_suggestion():
    llm = FakeLLM([OutfitSuggestion(item_ids=[1], explanation="ок")])
    advisor = OutfitAdvisor(llm)
    s = await advisor.suggest(profile=UserProfile(id=1), wardrobe=[_item(1, "coat")])
    assert s.item_ids == [1]
    assert llm.calls[0]["schema"] is OutfitSuggestion


# ── Сервис ──────────────────────────────────────────────────────────────────


async def _profile_with_location() -> ProfileService:
    ur = FakeUserRepo()
    await ur.get_or_create(1)
    await ur.set_location(1, 55.75, 37.62)
    return ProfileService(ur, FakeLLM(), FakeStorage())


@pytest.mark.asyncio
async def test_outfit_service_uses_weather_trends_and_confirms_worn():
    profile = await _profile_with_location()
    repo = FakeWardrobeRepo()
    await repo.add_item(1, attrs("coat"))  # id=1
    wardrobe = WardrobeService(repo, FakeLLM(), FakeStorage())
    weather = FakeWeather({"temperature_2m": 8})
    trend_provider = FakeTrendProvider()
    trends = TrendService(trend_provider, FakeTrendCache(), ttl_days=7)
    advisor = OutfitAdvisor(FakeLLM([OutfitSuggestion(item_ids=[1], explanation="ок")]))

    service = OutfitService(profile, wardrobe, weather, trends, advisor)
    suggestion, by_id = await service.suggest(1, occasion="прогулка")

    assert suggestion.item_ids == [1]
    assert weather.calls == [(55.75, 37.62)]      # погода по координатам профиля
    assert trend_provider.calls                    # тренды учтены
    assert repo.touched == [1]                      # носибельность подтверждена (§4.4)
    assert 1 in by_id


@pytest.mark.asyncio
async def test_outfit_service_requires_location():
    profile = ProfileService(FakeUserRepo(), FakeLLM(), FakeStorage())  # без координат
    service = OutfitService(
        profile,
        WardrobeService(FakeWardrobeRepo(), FakeLLM(), FakeStorage()),
        FakeWeather(),
        TrendService(None, FakeTrendCache()),
        OutfitAdvisor(FakeLLM()),
    )
    with pytest.raises(NeedLocation):
        await service.suggest(1)
