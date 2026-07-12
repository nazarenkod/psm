"""DI-контейнер: провайдеры + фабрика сессий БД, собранные один раз при старте.

Сервисы создаются на запрос внутри сессии (чистые границы, требования §10.2).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from aifashion.config import Settings
from aifashion.db.base import make_engine, make_session_factory
from aifashion.db.repositories import (
    SqlMessageRepository,
    SqlPhotoRepository,
    SqlTrendCacheRepository,
    SqlUserRepository,
    SqlWardrobeRepository,
)
from aifashion.engine.goal1_purchase import PurchaseAdvisor
from aifashion.engine.goal2_outfit import OutfitAdvisor
from aifashion.engine.goal3_capsule import CapsuleAdvisor
from aifashion.providers.registry import (
    get_embedder,
    get_image_gen,
    get_llm,
    get_storage,
    get_trends,
    get_weather,
)
from aifashion.services.capsule_service import CapsuleService
from aifashion.services.conversation_service import ConversationService
from aifashion.services.outfit_service import OutfitService
from aifashion.services.photo_intake import PhotoIntake
from aifashion.services.profile_service import ProfileService
from aifashion.services.purchase_service import PurchaseService
from aifashion.services.trend_service import TrendService
from aifashion.services.wardrobe_service import WardrobeService


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = make_engine(settings.database_url)
        self.session_factory = make_session_factory(self.engine)
        # Провайдеры — за Protocol; выбор реализации в реестре по конфигу.
        self.llm = get_llm(settings)
        self.weather = get_weather(settings)
        self.storage = get_storage(settings)
        self.embedder = get_embedder(settings)       # None — поиск дублей деградирует
        self.trends_provider = get_trends(settings)
        self.image_gen = get_image_gen(settings)     # None — капсула отдаётся текстом

    @asynccontextmanager
    async def unit_of_work(self):
        """Сессия + транзакция на один запрос."""
        async with self.session_factory() as session:
            async with session.begin():
                yield Services(self, session)

    async def dispose(self) -> None:
        await self.engine.dispose()


class Services:
    """Сервисы, собранные вокруг одной сессии БД."""

    def __init__(self, c: AppContainer, session: AsyncSession) -> None:
        self.profile = ProfileService(SqlUserRepository(session), c.llm, c.storage)
        self.wardrobe = WardrobeService(
            SqlWardrobeRepository(session), c.llm, c.storage, c.embedder
        )
        self.photo_intake = PhotoIntake(c.llm)
        self.photos = SqlPhotoRepository(session)
        self.storage = c.storage
        self.conversation = ConversationService(
            SqlMessageRepository(session), window=c.settings.history_window
        )

        trend_service = TrendService(
            c.trends_provider,
            SqlTrendCacheRepository(session),
            ttl_days=c.settings.trend_ttl_days,
        )
        self.purchase = PurchaseService(
            self.profile, self.wardrobe, PurchaseAdvisor(c.llm), self.conversation
        )
        self.outfit = OutfitService(
            self.profile, self.wardrobe, c.weather, trend_service,
            OutfitAdvisor(c.llm), self.conversation,
        )
        self.capsule = CapsuleService(
            self.profile, self.wardrobe, trend_service, CapsuleAdvisor(c.llm),
            self.conversation,
            image_gen=c.image_gen, storage=c.storage, image_size=c.settings.image_size,
        )
