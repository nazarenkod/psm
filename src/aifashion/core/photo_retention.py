"""Политика хранения фото по роли (требования §4.5).

Против захламления базы и ради гигиены персональных данных. Чистая логика —
сервис применяет решение, вызывая хранилище/репозиторий.
"""
from __future__ import annotations

from enum import Enum

from aifashion.core.models import PhotoRole

SELFIE_KEEP_LIMIT = 5  # сколько последних селфи держим для пере-вывода профиля


class RetentionAction(str, Enum):
    keep = "keep"                          # хранить оригинал долго
    keep_canonical = "keep_canonical"      # одно каноничное фото на вещь
    delete_after_extract = "delete_after_extract"  # удалить оригинал после извлечения признаков


def retention_action(role: PhotoRole) -> RetentionAction:
    """Что делать с оригиналом фото данной роли.

    - selfie: храним (но не все — старые сверх лимита чистятся отдельно, см.
      ``PhotoRepository.evictable_selfie_keys``);
    - product/reference: чужие/товарные фото — удаляем оригинал после извлечения;
    - flat-lay: своя вещь без человека — оставляем как каноничное фото вещи;
    - unknown: до уточнения роли держим.
    """
    match role:
        case PhotoRole.selfie:
            return RetentionAction.keep
        case PhotoRole.flat_lay:
            return RetentionAction.keep_canonical
        case PhotoRole.product_shot | PhotoRole.outfit_reference:
            return RetentionAction.delete_after_extract
        case _:
            return RetentionAction.keep
