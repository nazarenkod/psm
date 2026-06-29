# AI Fashion Manager

Telegram-бот — персональный стилист. MVP закрытой обкатки (1–5 человек по белому списку).

- **Требования:** [`REQUIREMENTS.md`](REQUIREMENTS.md)
- **Архитектура:** [`ARCHITECTURE.md`](ARCHITECTURE.md)

## Стек

Python 3.12 · aiogram 3 · Claude (`claude-opus-4-8`) через свой Protocol + Anthropic SDK ·
PostgreSQL 16 + pgvector · S3-совместимое хранилище (MinIO/R2) · Open-Meteo · docker-compose.

## Запуск (Docker)

```bash
cp .env.example .env          # заполни TELEGRAM_BOT_TOKEN и ANTHROPIC_API_KEY
docker compose up --build     # поднимет Postgres+pgvector, MinIO, применит миграции, запустит бота
```

Белый список: добавь свой Telegram ID в `WHITELIST_TELEGRAM_IDS` в `.env`
(или строки в таблицу `allowed_users`). Бот не отвечает тем, кого нет в списке.

## Разработка

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

pytest -q          # тесты (без БД/сети — на фейках)
ruff check .       # линт
alembic upgrade head   # миграции (нужен поднятый Postgres)
```

## Переключение моделей/провайдеров

Через переменные окружения — без правок кода:

```
LLM_PROVIDER=anthropic     # реализация LLM/Vision
LLM_MODEL=claude-opus-4-8  # модель в рамках провайдера
WEATHER_PROVIDER=open_meteo
STORAGE_PROVIDER=s3
```

Добавление нового провайдера = новая реализация Protocol'а + регистрация в
`src/aifashion/providers/registry.py`. См. `ARCHITECTURE.md`.

## Команды бота

- фото вещи / образа → добавить в гардероб;
- фото / ссылка / скриншот вещи к покупке (в т.ч. пересланный пост из канала) →
  вердикт «брать ли» с баллом и обоснованием (Цель 1);
- `/delete` → удалить все данные.

## Статус

Реализован шаг 1 (фундамент) + ядро **Цель 1 «Купить ли вещь»**. Цели 2 и 3 — следующие
(см. порядок сборки в `REQUIREMENTS.md` §14).
