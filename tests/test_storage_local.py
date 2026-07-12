import pytest

from aifashion.providers.storage.local_storage import LocalStorage


@pytest.mark.asyncio
async def test_put_writes_file(tmp_path):
    storage = LocalStorage(str(tmp_path))
    key = await storage.put("users/1/wardrobe/abc", b"hello", "image/jpeg")
    assert key == "users/1/wardrobe/abc"
    assert (tmp_path / "users/1/wardrobe/abc").read_bytes() == b"hello"


@pytest.mark.asyncio
async def test_delete_prefix_removes_user_files(tmp_path):
    storage = LocalStorage(str(tmp_path))
    await storage.put("users/1/wardrobe/a", b"x", "image/jpeg")
    await storage.put("users/1/capsule/b", b"y", "image/png")
    await storage.put("users/2/wardrobe/c", b"z", "image/jpeg")  # чужие данные

    removed = await storage.delete_prefix("users/1/")

    assert removed == 2
    assert not (tmp_path / "users/1").exists()
    assert (tmp_path / "users/2/wardrobe/c").exists()  # изоляция: чужое не тронуто


@pytest.mark.asyncio
async def test_delete_prefix_missing_is_noop(tmp_path):
    storage = LocalStorage(str(tmp_path))
    assert await storage.delete_prefix("users/999/") == 0
