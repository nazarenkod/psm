"""Цель 3 «Капсула и что докупить» (требования §7) + иллюстрация капсулы."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from aifashion.bot.container import AppContainer
from aifashion.engine.goal3_capsule import format_capsule

router = Router()


@router.message(Command("capsule"))
async def capsule(message: Message, container: AppContainer) -> None:
    await message.chat.do("typing")
    async with container.unit_of_work() as svc:
        result = await svc.capsule.build(message.from_user.id)

    text = format_capsule(result.plan)
    if result.image is not None:
        await message.answer_photo(
            BufferedInputFile(result.image, filename="capsule.png"), caption=text[:1024]
        )
    else:
        await message.answer(text)
