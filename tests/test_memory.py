import pytest

from aifashion.core.models import ConversationTurn, PurchaseVerdict
from aifashion.engine.goal1_purchase import PurchaseAdvisor
from aifashion.services.conversation_service import ConversationService
from aifashion.services.profile_service import ProfileService
from aifashion.services.purchase_service import PurchaseService
from aifashion.services.wardrobe_service import WardrobeService
from tests.fakes import (
    FakeLLM,
    FakeMessageRepo,
    FakeStorage,
    FakeUserRepo,
    FakeWardrobeRepo,
)


@pytest.mark.asyncio
async def test_conversation_records_and_reads():
    repo = FakeMessageRepo()
    svc = ConversationService(repo, window=20)
    await svc.record_user(1, "привет")
    await svc.record_assistant(1, "здравствуй")
    assert repo.records == [(1, "user", "привет"), (1, "assistant", "здравствуй")]


@pytest.mark.asyncio
async def test_purchase_feeds_history_and_records_dialogue():
    msg_repo = FakeMessageRepo()
    msg_repo.preload = [ConversationTurn(role="user", text="вчера скидывал пальто")]
    conversation = ConversationService(msg_repo)

    profile = ProfileService(FakeUserRepo(), FakeLLM(), FakeStorage())
    wardrobe = WardrobeService(FakeWardrobeRepo(), FakeLLM(), FakeStorage())
    advisor_llm = FakeLLM([PurchaseVerdict(buy=True, score=70, reasoning="ок")])
    service = PurchaseService(profile, wardrobe, PurchaseAdvisor(advisor_llm), conversation)

    await service.evaluate(1, item_link="http://shop/x")

    # история дошла до модели (память агента)
    assert advisor_llm.calls[0]["history"] == msg_repo.preload
    # диалог записан: запрос пользователя + ответ ассистента
    roles = [r for (_, r, _) in msg_repo.records]
    assert roles == ["user", "assistant"]
