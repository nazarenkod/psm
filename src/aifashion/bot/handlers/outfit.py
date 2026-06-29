"""Цель 2 «Что надеть сейчас» (требования §6) + автогеолокация для погоды."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from aifashion.bot.container import AppContainer
from aifashion.engine.goal2_outfit import format_outfit
from aifashion.services.outfit_service import NeedLocation

router = Router()


def _location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Поделиться геолокацией", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@router.message(Command("outfit"))
async def outfit(message: Message, command: CommandObject, container: AppContainer) -> None:
    occasion = (command.args or "").strip() or None
    await message.chat.do("typing")
    try:
        async with container.unit_of_work() as svc:
            suggestion, by_id = await svc.outfit.suggest(message.from_user.id, occasion=occasion)
    except NeedLocation:
        await message.answer(
            "Чтобы учесть погоду, поделись геолокацией:",
            reply_markup=_location_keyboard(),
        )
        return
    await message.answer(format_outfit(suggestion, by_id))


@router.message(F.location)
async def save_location(message: Message, container: AppContainer) -> None:
    loc = message.location
    async with container.unit_of_work() as svc:
        await svc.profile.set_location(message.from_user.id, loc.latitude, loc.longitude)
    await message.answer(
        "Локация сохранена. Напиши /outfit — подберу образ на сегодня.",
        reply_markup=ReplyKeyboardRemove(),
    )
