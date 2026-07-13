"""Единая конфигурация. Все технические выборы (раздел 12) — здесь."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    telegram_bot_token: str = ""
    whitelist_telegram_ids: str = ""  # "111,222,333"

    # Провайдеры моделей — переключение в одном месте (раздел 10.2)
    llm_provider: str = "anthropic"
    llm_model: str = "claude-opus-4-8"
    anthropic_api_key: str = ""

    weather_provider: str = "open_meteo"

    # Эмбеддинги для поиска дублей (требования §5). "none" — отключить.
    embedding_provider: str = "voyage"
    embedding_model: str = "voyage-3"
    voyage_api_key: str = ""

    # Анализ актуальных трендов (чтобы лук был современным).
    trend_provider: str = "anthropic"
    trend_ttl_days: int = 7  # тренды меняются медленно — кэшируем

    # Генерация изображений капсулы. Claude не умеет — идём через OpenAI. "none" — отключить.
    image_gen_provider: str = "openai"
    image_model: str = "gpt-image-2"
    image_size: str = "1024x1024"
    openai_api_key: str = ""

    # Память общения: сколько последних реплик подаём модели для контекста.
    history_window: int = 20

    # БД
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/aifashion"

    # Хранилище фото
    storage_provider: str = "local"          # local (MVP) | s3
    local_storage_dir: str = "./data/media"  # каталог для локального хранилища
    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket: str = "aifashion"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"

    log_level: str = "INFO"          # INFO для обычной работы, DEBUG — видеть промпты/ответы
    log_format: str = "console"      # console (читаемо) | json (для сбора логов)

    @property
    def whitelist_ids(self) -> set[int]:
        raw = self.whitelist_telegram_ids.strip()
        if not raw:
            return set()
        return {int(x) for x in raw.split(",") if x.strip()}


settings = Settings()
