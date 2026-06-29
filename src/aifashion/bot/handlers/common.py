"""Базовые команды: /start, /help, /delete (требования §10)."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from aifashion.bot.container import AppContainer

router = Router()

_HELP = (
    "Я помогу с гардеробом:\n"
    "• пришли фото вещи или образа — добавлю в гардероб;\n"
    "• пришли фото/ссылку/скриншот вещи к покупке — скажу, брать ли (Цель 1);\n"
    "• /delete — удалить все мои данные о тебе.\n"
)


@router.message(Command("start"))
async def start(message: Message, container: AppContainer) -> None:
    lang = message.from_user.language_code if message.from_user else None
    async with container.unit_of_work() as svc:
        await svc.profile.get_or_create(message.from_user.id, lang)
    await message.answer("Привет! " + _HELP)


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(_HELP)


@router.message(Command("delete"))
async def delete(message: Message, container: AppContainer) -> None:
    uid = message.from_user.id
    async with container.unit_of_work() as svc:
        await svc.profile.delete_everything(uid)
    # блобы фото — отдельным вызовом хранилища (вне транзакции БД)
    await container.storage.delete_prefix(f"users/{uid}/")
    await message.answer("Готово. Все твои данные удалены.")
