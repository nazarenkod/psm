# Архитектура

Модульный монолит, один процесс. Принцип (требования §10.2): **готовность к росту =
чистые швы между модулями, а не тяжёлая инфраструктура заранее.**

## Поток

```
Telegram (aiogram)
  └─ middleware: белый список по Telegram ID  ──► чужих отсекаем до логики (§10)
  └─ handlers (диалоги по целям)
        │
        ▼
  services:  profile · wardrobe · photo_intake        ◄── фундамент (§4)
        │
        ▼
  engine:    goal1_purchase  (далее goal2_outfit, goal3_capsule)
        │
        ▼
  providers (за Protocol, выбор по env):
     LLMProvider(anthropic) · WeatherProvider(open_meteo) · StorageProvider(s3)
        │
        ▼
  db (SQLAlchemy async + Alembic):  всё привязано к user_id (§10)
```

## Слои и зависимости

| Пакет | Ответственность | От чего зависит |
|---|---|---|
| `core/models` | доменные типы (value + сущности) | только pydantic |
| `core/ports` | порты репозиториев (Protocol) | `core/models` |
| `core/access`, `core/photo_retention` | чистая логика (белый список, хранение фото) | — |
| `providers/base` | порты внешних сервисов (Protocol) | `core/models` |
| `providers/*` | адаптеры (Anthropic, Open-Meteo, S3) | конкретные SDK |
| `providers/registry` | выбор реализации по конфигу | `config`, `providers/base` |
| `services/*` | сценарии фундамента | `core/ports`, `providers/base` |
| `engine/*` | три цели | `providers/base`, `core/models` |
| `db/*` | ORM + реализации портов | SQLAlchemy, pgvector |
| `bot/*` | Telegram-слой, DI-контейнер | всё выше |

Ключ: **бизнес-логика (`services`, `engine`) зависит только от Protocol'ов**, не от
SDK и не от ORM. Поэтому она тестируется на фейках без БД, сети и Anthropic.

## Переключение моделей и провайдеров (§11)

1. Интерфейсы — `providers/base.py` (`LLMProvider`, `WeatherProvider`, `StorageProvider`)
   и `core/ports.py` (репозитории).
2. Реализации — `providers/llm/anthropic_provider.py` и т.д. Импортируются **лениво**.
3. Выбор — `providers/registry.py`: словарь `имя → фабрика`, имя берётся из env
   (`LLM_PROVIDER`, `LLM_MODEL`, `WEATHER_PROVIDER`, `STORAGE_PROVIDER`).

Сменить провайдера/модель = добавить реализацию + поменять env. **Ноль правок в
бизнес-логике.** Маршрутизация задач по разным моделям (дешёвая на разбор фото,
сильная на вердикт) добавляется здесь же, позже, без переписывания.

## Инварианты, вшитые в код (а не в промпт)

- **Изоляция по `user_id`** — каждый метод репозитория фильтрует по пользователю (§10).
- **Role-tagging** — внешность учится только из selfie: единственная точка —
  `ProfileService.learn_appearance_from_selfie`, она отвергает не-selfie (§4.2).
- **Независимость вердикта** — в `engine/goal1_purchase` нет ничего про партнёрку (§2).
- **`/delete`** — каскад в БД + `storage.delete_prefix` по префиксу пользователя (§10).
- **Хранение фото по роли** — `core/photo_retention` (§4.5).

## Тестирование

`tests/fakes.py` — фейковые провайдеры/репозитории. Юнит-тесты покрывают чистую
логику, движок Цели 1 и сервисы без внешних систем. Реализации на SQLAlchemy —
интеграционный слой (тестируются на реальном Postgres, в CI отдельным прогоном).

```
pytest -q
```

## Что НЕ делаем в MVP

Очереди, кэши, балансировщики, шардирование, микросервисы, админка, биллинг,
регистрация, автоматический мониторинг каналов (§3, §10.2). Планировщик (APScheduler)
внутрипроцессный — он функциональное требование удержания (§9), а не масштабирование.
