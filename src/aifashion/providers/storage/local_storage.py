"""Локальное файловое хранилище. Реализует StorageProvider.

Для MVP проще, чем S3: фото лежат в каталоге на диске. Тот же интерфейс, что и
S3-адаптер — переключение по env, без изменений бизнес-логики.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path


class LocalStorage:
    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        def _write() -> None:
            path = self._base / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_write)
        return key

    async def delete_prefix(self, prefix: str) -> int:
        def _delete() -> int:
            target = self._base / prefix
            if not target.exists() or not target.is_dir():
                return 0
            count = sum(1 for f in target.rglob("*") if f.is_file())
            shutil.rmtree(target)
            return count

        return await asyncio.to_thread(_delete)
