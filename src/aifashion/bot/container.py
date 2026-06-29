"""DI-контейнер: провайдеры + фабрика сессий БД, собранные один раз при старте.

Сервисы создаются на запрос внутри сессии (чистые границы, требования §10.2).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from aifashion.config import Settings
from aifashion.db.base import make_engine, make_session_factory
from aifashion.db.repositories import (
    SqlPhotoRepository,
    SqlUserRepository,
    SqlWardrobeRepository,
)
from aifashion.engine.goal1_purchase import PurchaseAdvisor
from aifashion.providers.registry import get_llm, get_storage, get_weather
from aifashion.services.photo_intake import PhotoIntake
from aifashion.services.profile_service import ProfileService
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
        self.wardrobe = WardrobeService(SqlWardrobeRepository(session), c.llm, c.storage)
        self.photo_intake = PhotoIntake(c.llm)
        self.advisor = PurchaseAdvisor(c.llm)
        self.photos = SqlPhotoRepository(session)
        self.storage = c.storage
