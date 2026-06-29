import pytest

from aifashion.config import Settings
from aifashion.providers.registry import get_llm, get_storage, get_weather


def test_unknown_llm_provider_raises():
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        get_llm(Settings(llm_provider="nope"))


def test_unknown_weather_provider_raises():
    with pytest.raises(ValueError, match="WEATHER_PROVIDER"):
        get_weather(Settings(weather_provider="nope"))


def test_unknown_storage_provider_raises():
    with pytest.raises(ValueError, match="STORAGE_PROVIDER"):
        get_storage(Settings(storage_provider="nope"))
