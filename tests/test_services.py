import pytest

from aifashion.core.models import (
    AppearanceAnalysis,
    ExtractedItems,
    PhotoRole,
    SilhouetteHints,
    WardrobeItemAttrs,
)
from aifashion.services.photo_intake import NeedsRoleClarification, PhotoIntake
from aifashion.services.profile_service import ProfileService
from aifashion.services.wardrobe_service import WardrobeService
from tests.fakes import FakeLLM, FakeStorage, FakeUserRepo, FakeWardrobeRepo, attrs, img


# ── Гардероб ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_from_photo_stores_blob_and_item():
    repo, storage = FakeWardrobeRepo(), FakeStorage()
    llm = FakeLLM([attrs("coat", color="beige")])
    svc = WardrobeService(repo, llm, storage)

    item = await svc.add_from_photo(user_id=1, image=img())

    assert item.attrs.category == "coat"
    assert item.photo_key in storage.objects  # фото сохранено
    assert repo.items == [item]


@pytest.mark.asyncio
async def test_parse_look_creates_all_items():
    repo, storage = FakeWardrobeRepo(), FakeStorage()
    llm = FakeLLM(
        [ExtractedItems(items=[WardrobeItemAttrs(category="shirt"), WardrobeItemAttrs(category="jeans")])]
    )
    svc = WardrobeService(repo, llm, storage)

    items = await svc.parse_look(user_id=1, image=img())

    assert [i.attrs.category for i in items] == ["shirt", "jeans"]


# ── Профиль: критический инвариант §4.2 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_appearance_learns_only_from_selfie():
    svc = ProfileService(FakeUserRepo(), FakeLLM(), FakeStorage())
    for role in (PhotoRole.outfit_reference, PhotoRole.product_shot, PhotoRole.flat_lay):
        with pytest.raises(ValueError):
            await svc.learn_appearance_from_selfie(1, img(), role)


@pytest.mark.asyncio
async def test_selfie_updates_appearance():
    repo = FakeUserRepo()
    llm = FakeLLM(
        [
            AppearanceAnalysis(
                color_type="зима",
                contrast="высокая",
                silhouette=SilhouetteHints(recommendations=["удлиняй низ"]),
            )
        ]
    )
    svc = ProfileService(repo, llm, FakeStorage())

    profile = await svc.learn_appearance_from_selfie(1, img(), PhotoRole.selfie)

    assert profile.color_type == "зима"
    assert profile.silhouette.recommendations == ["удлиняй низ"]


@pytest.mark.asyncio
async def test_delete_returns_blob_keys():
    repo = FakeUserRepo()
    svc = ProfileService(repo, FakeLLM(), FakeStorage())
    keys = await svc.delete_everything(1)
    assert repo.deleted == [1]
    assert keys  # ключи для чистки хранилища


# ── Приём фото / role-tagging §4.2 ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_intake_returns_confident_role():
    from aifashion.core.models import PhotoClassification

    intake = PhotoIntake(FakeLLM([PhotoClassification(role=PhotoRole.selfie, confident=True)]))
    result = await intake.classify(img())
    assert result.role is PhotoRole.selfie


@pytest.mark.asyncio
async def test_intake_asks_when_unsure():
    from aifashion.core.models import PhotoClassification

    intake = PhotoIntake(FakeLLM([PhotoClassification(role=PhotoRole.selfie, confident=False)]))
    with pytest.raises(NeedsRoleClarification):
        await intake.classify(img())
