"""Сборка aiogram Dispatcher: middleware белого списка + роутеры."""
from __future__ import annotations

from aiogram import Dispatcher

from aifashion.bot.container import AppContainer
from aifashion.bot.handlers import common, outfit, purchase
from aifashion.bot.middlewares.whitelist import WhitelistMiddleware


def build_dispatcher(container: AppContainer) -> Dispatcher:
    dp = Dispatcher()
    dp["container"] = container  # инъекция в хендлеры по имени параметра

    whitelist = WhitelistMiddleware(container)
    dp.message.middleware(whitelist)
    dp.callback_query.middleware(whitelist)

    # порядок важен: команды и геолокация раньше «всё остальное → оценка покупки»
    dp.include_router(common.router)
    dp.include_router(outfit.router)
    dp.include_router(purchase.router)
    return dp
