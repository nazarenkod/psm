"""Цель 1 «Купить ли вещь» (требования §5) — реактивный вход.

Принимает фото / ссылку / скриншот, в т.ч. пересланный пост из канала (§12,
реактивный режим). Возвращает вердикт с баллом и обоснованием.
"""
from __future__ import annotations

import base64

from aiogram import Bot, F, Router
from aiogram.types import Message

from aifashion.bot.container import AppContainer
from aifashion.core.models import ImageInput
from aifashion.engine.goal1_purchase import format_verdict

router = Router()


async def _photo_to_image(bot: Bot, message: Message) -> ImageInput | None:
    if not message.photo:
        return None
    file_id = message.photo[-1].file_id  # самое большое разрешение
    buf = await bot.download(file_id)
    data = buf.read() if buf else b""
    return ImageInput(media_type="image/jpeg", data_b64=base64.b64encode(data).decode())


@router.message(F.photo | F.text)
async def evaluate_purchase(message: Message, bot: Bot, container: AppContainer) -> None:
    uid = message.from_user.id
    image = await _photo_to_image(bot, message)
    text = (message.text or message.caption or "").strip()
    item_link = text if text.startswith("http") else None
    note = None if item_link else (text or None)

    if image is None and not item_link and not note:
        await message.answer("Пришли фото вещи, ссылку или скриншот — оценю покупку.")
        return

    await message.chat.do("typing")
    async with container.unit_of_work() as svc:
        profile = await svc.profile.get_or_create(uid)
        wardrobe = await svc.wardrobe.summary_for_prompt(uid)
        verdict = await svc.advisor.evaluate(
            profile=profile,
            wardrobe=wardrobe,
            images=[image] if image else None,
            item_link=item_link,
            note=note,
        )
    await message.answer(format_verdict(verdict))
