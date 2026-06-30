# Структура проекта и иерархия модулей

Поток обработки и инженерные решения — в [architecture.md](architecture.md).

## Модули, сервисы и публичный API

Бизнес-логика организована в **модули** (по бизнес-областям), каждый модуль — из
**сервисов**:

- **Сервис** = класс с одной ответственностью: логика прямо в классе, зависимости
  инжектятся через конструктор в DI-контейнере (`src/di/container.py`, без сторонних
  библиотек), `get_container()` — singleton на процесс.
- **Публичный API пакета** задаётся через `__init__.py`: он экспортирует сервис-класс и
  его DTO (`__all__`). Всё, что не экспортировано (сам модуль сервиса, мапперы), —
  внутреннее. Импортируют через пакет:
  `from modules.Backend.Payment.PaymentRepository import PaymentRepositoryService, PaymentFindTransfer`.
- **DTO сервиса** — рядом, в `dto.py` пакета; каждый сервис принимает на вход **свой**
  DTO (не сквозной чужой). Контракт расширения — в `Plugin/` (напр. провайдер оплаты).
- Границы зафиксированы машиной — **import-linter** (см. [development.md](development.md)).

Внутри пакета модуль импортирует **свой** `dto` по подмодулю (`.dto`), а чужие сервисы/
DTO — через их пакет; так публичный реэкспорт в `__init__` не создаёт циклов импорта.

## Дерево

```
src/
  worker/            точки входа (тонкие адаптеры; собирают сервисы из DI и зовут их):
                       api (FastAPI ASGI) · consumer (FastStream) · relay (poll-loop)
  modules/
    Backend/         бизнес-модули (в каждом сервис-пакет: <service>.py · dto.py · __init__)
      Payment/
        PaymentRepository/   чтение/запись платежа (PaymentRepositoryService)
        PaymentCreate/       создание платежа + событие в outbox (PaymentCreator)
        PaymentExecute/      проведение через шлюз + Plugin/ (контракт провайдера)
        PaymentProcessing/   обработка в consumer'е (PaymentProcessor)
        MockPaymentExecute/  эмуляция шлюза — плагин, реализующий контракт PaymentExecute
      Notification/    доставка webhook (WebhookNotificationSender)
      Outbox/
        OutboxPaymentRepository/  запись/чтение payment_outbox
        OutboxRelay/              докачка событий в брокер (OutboxRelay)
      Idempotency/
        PaymentProviderIdempotencyStoreRepository/  стор результата charge (дедуп)
    Frontend/        presentation-модули
      Request/RequestProcessingService/  routes · schemas (Pydantic) · dependencies (X-API-Key, DI-провайдеры)
  repository/        ORM-независимый слой персистентности:
                       entity (бизнес-сущности) · *_repository_interface (порты, ABC) ·
                       *_repository (SQLAlchemy-адаптеры, реализуют порты) ·
                       enum (статусы, типы, routing_key — persisted-значения)
  infrastructure/    адаптеры за портами (каждый — пакет с публичным __init__):
                       Persistence (engine/session/UnitOfWork, ORM) · Http (webhook-клиент) ·
                       Messaging (broker, topology + naming exchange/queue/header, publisher)
  shared/            Port (UnitOfWork, Transaction, MessagePublisher, HttpClientInterface,
                       DuplicateKeyError) · Dto (ContextTransfer, rabbitmq-трансферы)
  config/            настройки (yaml + env, get_settings)
  di/                DI-контейнер (композиционный корень)
migrations/          Alembic: payments · payment_outbox · payment_provider_idempotency_store
tests/               integration (testcontainers: БД + очереди) · api · unit
pyproject.toml       конфиг ruff / mypy / import-linter   ·   Makefile — задачи качества
```

## Слои и направление зависимостей

```
worker  →  modules (публичный API пакетов)  →  repository / infrastructure
                                                (за портами из shared/Port)
              ▲ зависимости собирает DI-контейнер (инжектит адаптеры в сервисы)
```

- `worker` — тонкие адаптеры точек входа; берут сервисы из `get_container()`.
- Бизнес-слой (`modules/Backend`) зависит от **портов** (`shared/Port`), не от
  SQLAlchemy / RabbitMQ / httpx. Конкретные реализации живут в `infrastructure` и
  `repository` и инжектятся через DI. Домен не импортирует presentation/composition
  (`worker`, `di`, `Frontend`) — проверяется import-linter.
- `repository` принимает/возвращает **бизнес-сущности** (`repository/entity`), а не ORM:
  ORM-модели и маппинг изолированы в `infrastructure/Persistence`. Хэндл транзакции
  приходит как непрозрачный `Transaction` (порт) — приведение к `AsyncSession` локализовано
  в адаптере-репозитории (там, где инфраструктура и так известна).
- **Инверсия зависимостей**: домен-сервисы зависят от **репозиторных портов**
  (`repository/*_repository_interface.py`, ABC), а не от конкретных адаптеров. Адаптеры
  реализуют порты и инжектятся DI-контейнером. Поэтому у `modules.Backend` нет зависимости
  от `infrastructure` — даже транзитивной (зафиксировано контрактом import-linter).
- DTO — `dataclass`-трансферы; идентичность сущности (`id`/`created_at`) задаётся доменом
  (дефолтами), источник истины `created_at` — БД. Транзакция ходит в `ContextTransfer`.

## Точки входа (`worker/`)

| Процесс | Запуск | Роль |
|---|---|---|
| `api` | `uvicorn worker.api.main:app` | приём `POST`/`GET`, запись платежа+события в БД |
| `consumer` | `faststream run worker.consumer.main:app` | обработка `payments.new`: шлюз → статус → webhook, retry/DLQ |
| `relay` | `python -m worker.relay.main` | докачка `payment_outbox` → `payments.new` |
