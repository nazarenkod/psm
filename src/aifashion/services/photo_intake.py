"""Приём фото и role-tagging (требования §4.2).

Жёсткое требование: при неоднозначности система ОБЯЗАНА спросить, а не угадывать.
Поэтому при низкой уверенности модели бросаем ``NeedsRoleClarification`` — бот
задаёт уточняющий вопрос.
"""
from __future__ import annotations

from aifashion.core.models import ImageInput, PhotoClassification, PhotoRole
from aifashion.providers.base import LLMProvider

_SYSTEM = (
    "Определи природу фотографии одежды/человека. Возможные роли:\n"
    "- selfie: на фото сам пользователь (его лицо/фигура);\n"
    "- outfit_reference: чужой образ (блогер, знаменитость, прохожий);\n"
    "- product_shot: карточка товара, манекен, модель бренда;\n"
    "- flat_lay: вещь без человека (разложена/на вешалке).\n"
    "Если уверенности нет — верни confident=false. Не угадывай."
)


class NeedsRoleClarification(Exception):
    """Роль фото неоднозначна — нужно спросить пользователя."""


class PhotoIntake:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def classify(self, image: ImageInput) -> PhotoClassification:
        result = await self._llm.parse(
            system=_SYSTEM,
            prompt="Классифицируй это фото по роли.",
            schema=PhotoClassification,
            images=[image],
        )
        if not result.confident or result.role is PhotoRole.unknown:
            raise NeedsRoleClarification
        return result
