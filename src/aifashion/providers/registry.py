"""Реестр провайдеров — единственное место выбора реализации (требования §11).

Сменить провайдера/модель = поменять переменную окружения. Бизнес-логика
зависит только от Protocol'ов из ``base.py`` и не меняется.

Адаптеры импортируются лениво (внутри фабрик), чтобы, например, тесты движка не
тянули за собой boto3/anthropic.
"""
from __future__ import annotations

from collections.abc import Callable

from aifashion.config import Settings
from aifashion.providers.base import (
    EmbeddingProvider,
    ImageGenProvider,
    LLMProvider,
    StorageProvider,
    TrendProvider,
    WeatherProvider,
)


def _make_anthropic(s: Settings) -> LLMProvider:
    from aifashion.providers.llm.anthropic_provider import AnthropicProvider

    return AnthropicProvider(api_key=s.anthropic_api_key, model=s.llm_model)


def _make_open_meteo(_: Settings) -> WeatherProvider:
    from aifashion.providers.weather.open_meteo import OpenMeteoProvider

    return OpenMeteoProvider()


def _make_local(s: Settings) -> StorageProvider:
    from aifashion.providers.storage.local_storage import LocalStorage

    return LocalStorage(base_dir=s.local_storage_dir)


def _make_s3(s: Settings) -> StorageProvider:
    from aifashion.providers.storage.s3_storage import S3Storage

    return S3Storage(
        endpoint_url=s.s3_endpoint_url,
        bucket=s.s3_bucket,
        access_key=s.s3_access_key,
        secret_key=s.s3_secret_key,
        region=s.s3_region,
    )


_LLM: dict[str, Callable[[Settings], LLMProvider]] = {
    "anthropic": _make_anthropic,
    # "openai":  _make_openai,   # добавляется здесь, без правок бизнес-логики
}
_WEATHER: dict[str, Callable[[Settings], WeatherProvider]] = {
    "open_meteo": _make_open_meteo,
}
_STORAGE: dict[str, Callable[[Settings], StorageProvider]] = {
    "local": _make_local,
    "s3": _make_s3,
}


def get_llm(s: Settings) -> LLMProvider:
    try:
        return _LLM[s.llm_provider](s)
    except KeyError:
        raise ValueError(f"Неизвестный LLM_PROVIDER: {s.llm_provider}") from None


def get_weather(s: Settings) -> WeatherProvider:
    try:
        return _WEATHER[s.weather_provider](s)
    except KeyError:
        raise ValueError(f"Неизвестный WEATHER_PROVIDER: {s.weather_provider}") from None


def get_storage(s: Settings) -> StorageProvider:
    try:
        return _STORAGE[s.storage_provider](s)
    except KeyError:
        raise ValueError(f"Неизвестный STORAGE_PROVIDER: {s.storage_provider}") from None


def get_embedder(s: Settings) -> EmbeddingProvider | None:
    """None — если эмбеддинги отключены или нет ключа (поиск дублей деградирует мягко)."""
    if s.embedding_provider in ("none", ""):
        return None
    if s.embedding_provider == "voyage":
        if not s.voyage_api_key:
            return None
        from aifashion.providers.embedding.voyage import VoyageEmbedder

        return VoyageEmbedder(api_key=s.voyage_api_key, model=s.embedding_model)
    raise ValueError(f"Неизвестный EMBEDDING_PROVIDER: {s.embedding_provider}")


def get_trends(s: Settings) -> TrendProvider | None:
    if s.trend_provider in ("none", ""):
        return None
    if s.trend_provider == "anthropic":
        if not s.anthropic_api_key:
            return None
        from aifashion.providers.trends.anthropic_trends import AnthropicTrendProvider

        return AnthropicTrendProvider(api_key=s.anthropic_api_key, model=s.llm_model)
    raise ValueError(f"Неизвестный TREND_PROVIDER: {s.trend_provider}")


def get_image_gen(s: Settings) -> ImageGenProvider | None:
    """None — если генерация картинок отключена или нет ключа (капсула отдаётся текстом)."""
    if s.image_gen_provider in ("none", ""):
        return None
    if s.image_gen_provider == "openai":
        if not s.openai_api_key:
            return None
        from aifashion.providers.imagegen.openai_images import OpenAIImageGen

        return OpenAIImageGen(api_key=s.openai_api_key, model=s.image_model)
    raise ValueError(f"Неизвестный IMAGE_GEN_PROVIDER: {s.image_gen_provider}")
