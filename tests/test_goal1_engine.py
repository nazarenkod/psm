import pytest

from aifashion.core.models import PurchaseVerdict, UserProfile, WardrobeItem
from aifashion.engine.goal1_purchase import (
    SYSTEM_PROMPT,
    PurchaseAdvisor,
    build_prompt,
    format_verdict,
    summarize_wardrobe,
)
from tests.fakes import FakeLLM, attrs, img


def _item(cat, **kw):
    return WardrobeItem(id=1, user_id=1, attrs=attrs(cat, **kw))


def test_summary_empty_wardrobe_mentions_it():
    assert "пуст" in summarize_wardrobe([]).lower()


def test_summary_lists_categories():
    text = summarize_wardrobe([_item("sweater", color="grey"), _item("jeans")])
    assert "sweater" in text and "jeans" in text


def test_build_prompt_includes_profile_wardrobe_and_link():
    p = UserProfile(id=1, sex="м", lifestyle="офис")
    prompt = build_prompt(p, [_item("coat")], item_link="http://shop/x", note="скидка")
    assert "офис" in prompt
    assert "coat" in prompt
    assert "http://shop/x" in prompt
    assert "скидка" in prompt


def test_system_prompt_forbids_affiliate_influence():
    # §2: партнёрские интересы на вердикт не влияют
    assert "партнёр" in SYSTEM_PROMPT.lower()


def test_format_verdict_buy_and_details():
    v = PurchaseVerdict(buy=True, score=82, reasoning="хорошо сядет", uniqueness="дублей нет")
    out = format_verdict(v)
    assert "82/100" in out
    assert "хорошо сядет" in out
    assert "дублей нет" in out
    assert "Бери" in out


def test_format_verdict_reject():
    v = PurchaseVerdict(buy=False, score=20, reasoning="уже есть три похожих")
    assert "Не бери" in format_verdict(v)


@pytest.mark.asyncio
async def test_advisor_passes_images_and_schema():
    llm = FakeLLM([PurchaseVerdict(buy=False, score=10, reasoning="дубль")])
    advisor = PurchaseAdvisor(llm)
    image = img()
    verdict = await advisor.evaluate(
        profile=UserProfile(id=1), wardrobe=[_item("sweater")], images=[image]
    )
    assert verdict.buy is False
    call = llm.calls[0]
    assert call["schema"] is PurchaseVerdict
    assert call["images"] == [image]  # фото дошло до модели
    assert call["system"] == SYSTEM_PROMPT
