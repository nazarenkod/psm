"""Middleware белого списка (требования §10): бот не отвечает чужим."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from sqlalchemy import select

from aifashion.bot.container import AppContainer
from aifashion.core.access import is_allowed
from aifashion.db.models import AllowedUser


class WhitelistMiddleware(BaseMiddleware):
    def __init__(self, container: AppContainer) -> None:
        self._c = container

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None:
            return None
        async with self._c.session_factory() as session:
            db_ids = set((await session.scalars(select(AllowedUser.telegram_id))).all())
        if not is_allowed(
            user.id,
            static_whitelist=self._c.settings.whitelist_ids,
            db_allowed=db_ids,
        ):
            return None  # молчим — чужих нет в списке
        return await handler(event, data)
