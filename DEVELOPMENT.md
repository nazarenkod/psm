# Гайд разработчика

Практическое дополнение к [`ARCHITECTURE.md`](ARCHITECTURE.md): как устроен код и как
его дорабатывать по шаблону. Требования — в [`REQUIREMENTS.md`](REQUIREMENTS.md).

---

## Карта кода

```
src/aifashion/
├── config.py                 # все настройки (env) в одном месте
├── main.py                   # точка входа: проверка ключей + лог readiness + polling
│
├── core/                     # доменное ядро, зависит только от pydantic
│   ├── models.py             #   value-объекты и сущности (PurchaseVerdict, WardrobeItem, ...)
│   ├── ports.py              #   Protocol-порты репозиториев (UserRepository, ...)
│   ├── access.py             #   чистая логика белого списка
│   ├── photo_retention.py    #   политика хранения фото по роли
│   └── signatures.py         #   сигнатура вещи для эмбеддинга/дублей
│
├── providers/                # внешний мир за Protocol'ами
│   ├── base.py               #   ПОРТЫ: LLMProvider, WeatherProvider, StorageProvider,
│   │                         #          EmbeddingProvider, TrendProvider, ImageGenProvider
│   ├── registry.py           #   ВЫБОР реализации по env (единственное место)
│   ├── llm/anthropic_provider.py
│   ├── weather/open_meteo.py
│   ├── storage/{local,s3}_storage.py
│   ├── embedding/voyage.py
│   ├── trends/anthropic_trends.py
│   └── imagegen/openai_images.py
│
├── services/                 # сценарии; зависят от портов + провайдеров (не от SDK/ORM)
│   ├── profile_service.py    #   внешность учится только из selfie (инвариант §4.2)
│   ├── wardrobe_service.py    #   добавление/разбор лука/дубли/носибельность
│   ├── photo_intake.py        #   role-tagging (при неоднозначности — спросить)
│   ├── purchase_service.py    #   оркестрация Цели 1
│   ├── outfit_service.py      #   оркестрация Цели 2
│   ├── capsule_service.py     #   оркестрация Цели 3 (+ генерация картинки)
│   ├── trend_service.py       #   тренды с кэшем по TTL
│   └── conversation_service.py#   память общения (окно N ходов)
│
├── engine/                   # три цели — чистые функции + advisor'ы поверх LLMProvider
│   ├── goal1_purchase.py     #   «купить ли вещь»
│   ├── goal2_outfit.py       #   «что надеть»
│   └── goal3_capsule.py      #   «капсула»
│
├── db/                       # SQLAlchemy async: реализации портов
│   ├── base.py               #   engine/session
│   ├── models.py             #   ORM-таблицы (всё с user_id)
│   └── repositories.py       #   Sql*Repository — реализуют core/ports
│
└── bot/                      # Telegram-слой
    ├── container.py          #   DI: провайдеры (при старте) + сервисы (на запрос)
    ├── dispatcher.py         #   сборка Dispatcher, порядок роутеров
    ├── middlewares/whitelist.py
    └── handlers/{common,purchase,outfit,capsule}.py

alembic/versions/            # миграции БД (0001 схема, 0002 тренды, 0003 сообщения)
tests/                       # юнит-тесты на фейках (tests/fakes.py) — без БД/сети/ключей
```

---

## Ключевые правила (соблюдай при доработке)

1. **Бизнес-логика зависит только от Protocol'ов.** `services/` и `engine/` импортируют
   `core/ports.py` и `providers/base.py`, но НЕ `anthropic`, `boto3`, `sqlalchemy`. Так всё
   тестируется на фейках.
2. **Один выбор реализации — в `providers/registry.py`.** Адаптеры импортируются лениво
   (внутри фабрик), чтобы тесты движка не тянули тяжёлые SDK.
3. **Изоляция по `user_id`.** Каждый метод репозитория принимает `user_id` и фильтрует по нему.
4. **Мягкая деградация.** Опциональные провайдеры (эмбеддер, тренды, генератор картинок)
   могут быть `None` — код обязан работать и без них.
5. **Инварианты — в коде, не в промпте.** Пример: внешность учится только из selfie
   (`ProfileService.learn_appearance_from_selfie` отвергает не-selfie).
6. **Чистые функции — отдельно от IO.** Построение промптов и форматирование ответов
   (`build_prompt`, `format_*`) — чистые, покрыты тестами; advisor'ы поверх них зовут LLM.

---

## Рецепты

### Добавить нового провайдера модели (напр. LLM = OpenAI)

Пример: переключить/добавить LLM. 3 шага, бизнес-логику не трогаем.

1. **Реализация** — новый файл, реализующий Protocol из `providers/base.py`:
   ```python
   # providers/llm/openai_provider.py
   class OpenAIProvider:
       async def parse(self, *, system, prompt, schema, images=None, history=None): ...
       async def complete(self, *, system, prompt, images=None, history=None): ...
   ```
2. **Регистрация** — в `providers/registry.py` добавить в словарь и/или фабрику:
   ```python
   _LLM["openai"] = lambda s: OpenAIProvider(api_key=s.openai_api_key, model=s.llm_model)
   ```
3. **Конфиг** — при необходимости новые поля в `config.py` и `.env.example`.

Переключение: `LLM_PROVIDER=openai` в `.env`. Всё. То же для weather/storage/embedding/
trends/imagegen — у каждого свой словарь/геттер в реестре.

### Добавить новую «цель» (движок + сервис + команда + тесты)

1. **Схема ответа** — в `core/models.py` (например `class LookbookPlan(BaseModel): ...`).
2. **Движок** — `engine/goalN_*.py`: чистые `build_prompt(...)`, `format_*(...)` + класс
   `Advisor` с методом, зовущим `llm.parse(system=..., schema=..., history=...)`.
3. **Сервис** — `services/*_service.py`: собирает контекст (профиль, гардероб, тренды,
   история), зовёт advisor, пишет диалог через `ConversationService`.
4. **Контейнер** — собрать сервис в `bot/container.py` → `Services.__init__`.
5. **Хендлер** — `bot/handlers/*.py`, зарегистрировать роутер в `bot/dispatcher.py`
   (помни порядок: команды/локация раньше, «текст/фото → покупка» последним).
6. **Тесты** — на фейках: чистые функции движка + сервис с `FakeLLM`/фейк-репозиториями.

### Добавить таблицу в БД

1. **ORM** — класс в `db/models.py` (обязательно `user_id` + `ForeignKey(..., ondelete="CASCADE")`).
2. **Порт** — Protocol в `core/ports.py` (методы принимают `user_id`).
3. **Реализация** — `Sql*Repository` в `db/repositories.py`.
4. **Миграция** — новый файл `alembic/versions/000N_*.py` с `down_revision` на предыдущую.
   (Автогенерация: `alembic revision --autogenerate -m "..."` при поднятом Postgres; либо
   руками по образцу `0002`/`0003`.)
5. Если появились блобы — учти их в `UserRepository.delete_all` / `storage.delete_prefix`
   (команда `/delete`, §10).

### Добавить команду бота

```python
# bot/handlers/foo.py
from aiogram import Router
from aiogram.filters import Command
router = Router()

@router.message(Command("foo"))
async def foo(message, container):                 # container инъектится по имени
    async with container.unit_of_work() as svc:    # сессия+транзакция
        ...                                         # svc.profile / svc.wardrobe / ...
```
Зарегистрировать `foo.router` в `bot/dispatcher.py`.

### Написать тест

Фейки — в `tests/fakes.py` (`FakeLLM`, `FakeWardrobeRepo`, `FakeEmbedder`, `FakeWeather`,
`FakeTrendProvider`, `FakeTrendCache`, `FakeMessageRepo`, `FakeImageGen`, ...).

```python
import pytest
from aifashion.services.purchase_service import PurchaseService
from tests.fakes import FakeLLM, ...

@pytest.mark.asyncio
async def test_something():
    llm = FakeLLM([<заготовленный ответ схемы>])
    ...  # собрать сервис на фейках, вызвать, проверить llm.calls / записи репозитория
```
`FakeLLM.parse` пишет каждый вызов в `.calls` (system/prompt/schema/images/history) и отдаёт
заготовленные ответы — удобно проверять, что в модель ушёл нужный контекст.

---

## Частые команды

```bash
# окружение
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

# тесты (без БД/сети/ключей — на фейках)
pytest -q

# синтаксис всего дерева
python -m compileall -q src

# линт
ruff check .

# миграции (нужен поднятый Postgres)
alembic upgrade head
alembic revision --autogenerate -m "описание"

# локальный запуск целиком
docker compose up --build
```

Тесты сознательно **не** ходят в БД/сеть: `conftest.py` кладёт `src/` в путь, а зависят
тесты только от pydantic — быстрый прогон и стабильность.

---

## Швы под роадмап (где дорабатывать, не переписывая)

| Задача | Куда встраивать |
|---|---|
| **Партнёрка «где купить»** (Цель 3) | новый порт `AffiliateProvider` в `providers/base.py` + адаптер + реестр; вызывать в `capsule_service`/реактивно после вердикта. Вердикт Цели 1 не трогать (§2). |
| **Планировщик** (ежедневное «что надеть», сезонная сверка, чистка фото §4.4/§4.5) | APScheduler в `main.py`; задачи дёргают существующие сервисы (`outfit`, `wardrobe.stale_items`, `photos.evictable_selfie_keys`). |
| **Image-эмбеддинги для дублей** | заменить реализацию `EmbeddingProvider` (эмбеддинг по фото, а не по сигнатуре); интерфейс и `find_similar` не меняются. |
| **Сжатие старой истории** | в `ConversationService`: при переполнении окна — резюмировать старое через `llm.complete` и хранить summary. |
| **Мониторинг каналов** (Фаза 2) | порт `ChannelSource` (MTProto-ридер) → тот же движок Цели 1/3; включается без переписывания. |
| **Маршрутизация моделей** (дешёвая на разбор фото, сильная на вердикт) | политика `задача → модель` в реестре/сервисах; порт `LLMProvider` уже готов. |

---

## Куда смотреть при отладке

- **Старт:** лог `readiness` (в `main.py`) — какие провайдеры активны/в деградации.
- **Чужие не получают ответ:** белый список — `bot/middlewares/whitelist.py` + `core/access.py`.
- **Пустой/битый вердикт:** `AnthropicProvider.parse` бросает при `parsed_output is None`
  (обычно refusal/лимит токенов) — смотри `stop_reason`.
- **Нет картинки капсулы:** `image_gen=off` в readiness → нет `OPENAI_API_KEY` или хост
  заблокирован сетевой политикой окружения.
