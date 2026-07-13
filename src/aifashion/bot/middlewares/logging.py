"""Middleware трейла входящих апдейтов: одна строка лога на сообщение.

Даёт хронологию «кто что прислал» для отладки, до бизнес-логики.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, User

log = structlog.get_logger()


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        kind = "photo" if isinstance(event, Message) and event.photo else "text"
        preview = None
        if isinstance(event, Message) and event.text:
            preview = event.text[:64]
        log.info("update", user_id=getattr(user, "id", None), kind=kind, text=preview)
        return await handler(event, data)
