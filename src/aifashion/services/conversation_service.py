"""Память общения: загрузка недавней истории + запись новых реплик.

Даёт агенту контекст прошлых сообщений («та вещь, что скидывал вчера»).
Окно — последние N ходов (§памяти); сжатие старого в резюме — позже.
"""
from __future__ import annotations

from aifashion.core.models import ConversationTurn
from aifashion.core.ports import MessageRepository


class ConversationService:
    def __init__(self, repo: MessageRepository, *, window: int = 20) -> None:
        self._repo = repo
        self._window = window

    async def history(self, user_id: int) -> list[ConversationTurn]:
        return await self._repo.recent(user_id, limit=self._window)

    async def record_user(self, user_id: int, text: str) -> None:
        await self._repo.add(user_id, "user", text)

    async def record_assistant(self, user_id: int, text: str) -> None:
        await self._repo.add(user_id, "assistant", text)
