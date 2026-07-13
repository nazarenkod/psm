"""Точка входа: один процесс — бот + (позже) планировщик (требования §10.2)."""
from __future__ import annotations

import asyncio

import structlog
from aiogram import Bot

from aifashion.bot.container import AppContainer
from aifashion.bot.dispatcher import build_dispatcher
from aifashion.config import settings
from aifashion.logging_setup import setup_logging

log = structlog.get_logger()


def _check_and_report(container: AppContainer) -> None:
    """Проверить обязательные ключи и залогировать состояние провайдеров.

    Обязательны: TELEGRAM_BOT_TOKEN и ключ LLM (ядро). Остальное опционально —
    при отсутствии ключа функция деградирует мягко, о чём и сообщаем.
    """
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан (.env)")
    if settings.llm_provider == "anthropic" and not settings.anthropic_api_key:
        raise SystemExit("ANTHROPIC_API_KEY не задан — LLM это ядро, без него никак (.env)")

    log.info(
        "readiness",
        storage=settings.storage_provider,
        llm=f"{settings.llm_provider}:{settings.llm_model}",
        embeddings="on" if container.embedder else "off (поиск дублей деградирует)",
        trends="on" if container.trends_provider else "off (лук без трендового слоя)",
        image_gen="on" if container.image_gen else "off (капсула текстом, без картинки)",
        whitelist=len(settings.whitelist_ids) or "из БД",
    )


async def run() -> None:
    setup_logging(settings.log_level, settings.log_format)
    container = AppContainer(settings)
    _check_and_report(container)

    bot = Bot(settings.telegram_bot_token)
    dp = build_dispatcher(container)

    log.info("bot.start")
    try:
        await dp.start_polling(bot)
    finally:
        await container.dispose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
