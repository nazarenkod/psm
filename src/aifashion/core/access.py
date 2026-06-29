"""Контроль доступа по белому списку (требования §10).

Чистая функция — без aiogram/БД, чтобы легко тестировать. Aiogram-middleware
(`bot/middlewares/whitelist.py`) лишь оборачивает её.
"""
from __future__ import annotations

from collections.abc import Iterable


def is_allowed(
    telegram_id: int,
    *,
    static_whitelist: Iterable[int] = (),
    db_allowed: Iterable[int] = (),
) -> bool:
    """Разрешён ли пользователь.

    Доступ — если Telegram ID есть в статическом списке из конфига ИЛИ в списке из БД.
    Бот не отвечает тем, кого нет ни там, ни там.
    """
    return telegram_id in set(static_whitelist) or telegram_id in set(db_allowed)
