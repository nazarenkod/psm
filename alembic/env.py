"""Alembic env (async). URL и metadata берём из приложения."""
from __future__ import annotations

import asyncio
import pathlib
import sys

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aifashion.config import settings  # noqa: E402
from aifashion.db import models  # noqa: E402,F401  (регистрирует таблицы)
from aifashion.db.base import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
