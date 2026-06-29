"""Сигнатура вещи для эмбеддинга/поиска дублей (требования §5).

Чистая функция: из атрибутов собираем стабильную текстовую сигнатуру, по которой
считается эмбеддинг. Похожие вещи (категория+цвет+стиль) дают близкие векторы —
так ловим «у тебя уже три похожих свитера».
"""
from __future__ import annotations

from aifashion.core.models import WardrobeItemAttrs


def item_signature_text(attrs: WardrobeItemAttrs) -> str:
    parts = [attrs.category]
    for value in (attrs.color, attrs.material, attrs.style, attrs.brand):
        if value:
            parts.append(value)
    return " ".join(parts)
