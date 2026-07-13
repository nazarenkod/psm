# AI Fashion Manager

Telegram-бот — персональный стилист. MVP закрытой обкатки (1–5 человек по белому списку).

- **Требования:** [`REQUIREMENTS.md`](REQUIREMENTS.md)
- **Архитектура:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Гайд разработчика (как дорабатывать):** [`DEVELOPMENT.md`](DEVELOPMENT.md)

## Стек

Python 3.12 · aiogram 3 · Claude (`claude-opus-4-8`) через свой Protocol + Anthropic SDK ·
PostgreSQL 16 + pgvector · локальное хранилище фото (по умолчанию; опц. S3/MinIO/R2) ·
Open-Meteo · docker-compose.

## Запуск (Docker)

```bash
cp .env.example .env          # заполни TELEGRAM_BOT_TOKEN и ANTHROPIC_API_KEY
docker compose up --build     # поднимет Postgres+pgvector, применит миграции, запустит бота
                              # фото — локально в томе media (S3 не нужен)
```

Белый список: добавь свой Telegram ID в `WHITELIST_TELEGRAM_IDS` в `.env`
(или строки в таблицу `allowed_users`). Бот не отвечает тем, кого нет в списке.

## Обкатка (минимум ключей)

| Ключ | Обязателен? | Для чего |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | да | бот |
| `ANTHROPIC_API_KEY` | да | ядро (все вердикты, образы, планы) |
| `VOYAGE_API_KEY` | нет | поиск дублей (без него — деградация) |
| `OPENAI_API_KEY` | нет | картинка капсулы (без него — капсула текстом) |

**Сегодня без OpenAI/Voyage** можно обкатать: добавление вещей, разбор лука, **Цель 1** (вердикт
покупки), **Цель 2** (`/outfit` — образ по погоде и трендам), **Цель 3** (`/capsule` — план
текстом), память общения, `/delete`. Картинки капсулы включатся, как только добавишь
`OPENAI_API_KEY`.

При старте бот пишет лог `readiness` — видно, какие провайдеры активны, а какие в деградации.

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
  вердикт «брать ли» с баллом, обоснованием и проверкой дублей (Цель 1);
- `/outfit [повод]` → образ на сегодня из имеющихся вещей с учётом погоды и
  актуальных трендов (Цель 2); при первом запросе попросит геолокацию;
- `/capsule` → капсула и план докупок с иллюстрацией (Цель 3);
- `/delete` → удалить все данные.

Агент помнит историю общения (последние N реплик) и учитывает её в советах.

## Мульти-провайдер

Рассуждения — на Claude, **генерация изображений — на OpenAI** (Claude картинки не умеет).
Разные порты (`LLMProvider`, `ImageGenProvider`, …), переключаются по env независимо:

```
LLM_PROVIDER=anthropic      LLM_MODEL=claude-opus-4-8
EMBEDDING_PROVIDER=voyage   # поиск дублей (VOYAGE_API_KEY)
TREND_PROVIDER=anthropic    # тренды через web_search
IMAGE_GEN_PROVIDER=openai   IMAGE_MODEL=gpt-image-2   # капсула (OPENAI_API_KEY)
```

## Статус

Реализованы: фундамент, **все три цели** (1 «Купить ли вещь» с поиском дублей; 2 «Что надеть» с
погодой и трендами; 3 «Капсула» с генерацией картинки через OpenAI) и **память общения**.
Партнёрка «где купить», планировщик и авто-мониторинг каналов — следующее (см. `REQUIREMENTS.md`).
