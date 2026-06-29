"""Точка входа: один процесс — бот + планировщик (требования §10.2)."""
from __future__ import annotations

import asyncio
import logging

import structlog
from aiogram import Bot

from aifashion.bot.container import AppContainer
from aifashion.bot.dispatcher import build_dispatcher
from aifashion.config import settings

log = structlog.get_logger()


async def run() -> None:
    logging.basicConfig(level=settings.log_level)
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан (.env)")

    container = AppContainer(settings)
    bot = Bot(settings.telegram_bot_token)
    dp = build_dispatcher(container)

    log.info("bot.start", llm_provider=settings.llm_provider, model=settings.llm_model)
    try:
        await dp.start_polling(bot)
    finally:
        await container.dispose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
