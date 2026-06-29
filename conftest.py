"""Делает пакет ``aifashion`` (из ``src/``) импортируемым в тестах без установки."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
