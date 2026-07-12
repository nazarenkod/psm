import pytest

from aifashion.core.models import CapsulePlan, UserProfile
from aifashion.engine.goal3_capsule import CapsuleAdvisor, format_capsule
from aifashion.services.capsule_service import CapsuleService
from aifashion.services.conversation_service import ConversationService
from aifashion.services.profile_service import ProfileService
from aifashion.services.trend_service import TrendService
from aifashion.services.wardrobe_service import WardrobeService
from tests.fakes import (
    FakeImageGen,
    FakeLLM,
    FakeMessageRepo,
    FakeStorage,
    FakeTrendCache,
    FakeTrendProvider,
    FakeUserRepo,
    FakeWardrobeRepo,
)


def _plan() -> CapsulePlan:
    return CapsulePlan(
        gaps=["светлая overshirt"],
        next_purchase="светлая overshirt",
        explanation="свяжет низ и верх",
        image_prompt="раскладка капсулы на нейтральном фоне",
    )


def test_format_capsule_has_gaps_next_and_explanation():
    out = format_capsule(_plan())
    assert "светлая overshirt" in out
    assert "Следующая покупка" in out
    assert "свяжет низ и верх" in out


@pytest.mark.asyncio
async def test_advisor_returns_plan_with_history():
    llm = FakeLLM([_plan()])
    advisor = CapsuleAdvisor(llm)
    plan = await advisor.plan(profile=UserProfile(id=1), wardrobe=[])
    assert plan.next_purchase == "светлая overshirt"
    assert llm.calls[0]["schema"] is CapsulePlan


def _services():
    profile = ProfileService(FakeUserRepo(), FakeLLM(), FakeStorage())
    wardrobe = WardrobeService(FakeWardrobeRepo(), FakeLLM(), FakeStorage())
    trends = TrendService(FakeTrendProvider(), FakeTrendCache())
    advisor = CapsuleAdvisor(FakeLLM([_plan()]))
    conversation = ConversationService(FakeMessageRepo())
    return profile, wardrobe, trends, advisor, conversation


@pytest.mark.asyncio
async def test_capsule_generates_image_and_stores():
    profile, wardrobe, trends, advisor, conversation = _services()
    image_gen, storage = FakeImageGen(), FakeStorage()
    service = CapsuleService(
        profile, wardrobe, trends, advisor, conversation,
        image_gen=image_gen, storage=storage,
    )

    result = await service.build(1)

    assert result.image == b"PNGDATA"
    assert image_gen.prompts == ["раскладка капсулы на нейтральном фоне"]  # промпт от Claude
    assert storage.objects  # картинка сохранена в хранилище


@pytest.mark.asyncio
async def test_capsule_degrades_without_image_gen():
    profile, wardrobe, trends, advisor, conversation = _services()
    service = CapsuleService(profile, wardrobe, trends, advisor, conversation, image_gen=None)

    result = await service.build(1)

    assert result.image is None          # без генератора — только текстовый план
    assert result.plan.next_purchase == "светлая overshirt"
