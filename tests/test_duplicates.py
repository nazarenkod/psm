import pytest

from aifashion.core.models import PurchaseVerdict, WardrobeItem
from aifashion.core.signatures import item_signature_text
from aifashion.engine.goal1_purchase import PurchaseAdvisor
from aifashion.services.profile_service import ProfileService
from aifashion.services.purchase_service import PurchaseService
from aifashion.services.wardrobe_service import WardrobeService
from tests.fakes import (
    FakeEmbedder,
    FakeLLM,
    FakeStorage,
    FakeUserRepo,
    FakeWardrobeRepo,
    attrs,
    img,
)


def test_signature_includes_distinguishing_attrs():
    sig = item_signature_text(attrs("sweater", color="grey", style="casual", brand="Acme"))
    assert "sweater" in sig and "grey" in sig and "casual" in sig and "Acme" in sig


@pytest.mark.asyncio
async def test_find_duplicates_uses_embedder_and_repo():
    repo, emb = FakeWardrobeRepo(), FakeEmbedder()
    repo.similar = [WardrobeItem(id=7, user_id=1, attrs=attrs("sweater", color="grey"))]
    svc = WardrobeService(repo, FakeLLM(), FakeStorage(), emb)

    found = await svc.find_duplicates(1, attrs("sweater", color="grey"))

    assert [i.id for i in found] == [7]
    assert emb.texts  # эмбеддинг считался по сигнатуре


@pytest.mark.asyncio
async def test_no_duplicates_without_embedder():
    repo = FakeWardrobeRepo()
    repo.similar = [WardrobeItem(id=7, user_id=1, attrs=attrs("sweater"))]
    svc = WardrobeService(repo, FakeLLM(), FakeStorage(), embedder=None)
    assert await svc.find_duplicates(1, attrs("sweater")) == []


@pytest.mark.asyncio
async def test_add_from_photo_stores_embedding():
    repo, emb = FakeWardrobeRepo(), FakeEmbedder()
    svc = WardrobeService(repo, FakeLLM([attrs("coat")]), FakeStorage(), emb)
    item = await svc.add_from_photo(1, img())
    assert repo.embeddings[item.id] is not None  # вектор сохранён для поиска дублей


@pytest.mark.asyncio
async def test_purchase_service_feeds_duplicates_into_verdict():
    repo, emb = FakeWardrobeRepo(), FakeEmbedder()
    repo.similar = [WardrobeItem(id=3, user_id=1, attrs=attrs("sweater", color="grey"))]
    wardrobe = WardrobeService(repo, FakeLLM([attrs("sweater", color="grey")]), FakeStorage(), emb)
    profile = ProfileService(FakeUserRepo(), FakeLLM(), FakeStorage())
    advisor_llm = FakeLLM([PurchaseVerdict(buy=False, score=15, reasoning="дубль")])
    service = PurchaseService(profile, wardrobe, PurchaseAdvisor(advisor_llm))

    verdict = await service.evaluate(1, image=img())

    assert verdict.buy is False
    # дубли дошли до промпта вердикта (уникальность §5)
    assert "похожие" in advisor_llm.calls[0]["prompt"].lower()
