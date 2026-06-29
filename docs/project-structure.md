# Структура проекта и иерархия модулей

Поток обработки и инженерные решения — в [architecture.md](architecture.md).

## Spryker-подход

Бизнес-логика организована в **модули**:

- **Модуль** = публичный `facade.py` (проксирует вызовы в нужный сервис) + папки-**сервисы**.
- **Сервис** = `facade.py` · `factory.py` · `Business/` (логика) [· `Plugin/` — контракт
  расширения, · `Dto/` — локальные трансферы].
- Фасады — **только проксирование**, никакой логики. Зависимости собираются в
  DI-контейнере (`src/di/container.py`, без сторонних библиотек), `get_container()` —
  singleton на процесс.

## Дерево

```
src/
  worker/            точки входа (тонкие адаптеры, зовут только фасады модулей):
                       api (FastAPI ASGI) · consumer (FastStream) · relay (poll-loop)
  modules/
    Backend/         бизнес-модули
      Payment/        PaymentFacade → PaymentRepository · PaymentCreate ·
                        PaymentProcessing · PaymentExecute (+Plugin: контракт провайдера)
      MockPaymentExecute/  эмуляция шлюза — плагин, реализующий контракт PaymentExecute
      Notification/   NotificationFacade → WebhookNotificationService (доставка webhook)
      Outbox/         OutboxFacade → OutboxPaymentRepository · OutboxRelay
      Idempotency/    IdempotencyFacade → PaymentProviderIdempotencyStoreRepository (дедуп charge)
      RabbitMq/       RabbitMqFacade → RabbitMqManagement (публикация в брокер)
    Frontend/        presentation-модули
      Request/        RequestFacade → RequestProcessingService (routes · schemas · dependencies)
  repository/        ORM-независимый слой персистентности:
                       entity (бизнес-сущности) · *_repository (SQLAlchemy-адаптеры) · enum
  infrastructure/    адаптеры за портами:
                       Persistence (engine/session/UnitOfWork, ORM) · Http (webhook-клиент) ·
                       Messaging (broker, topology)
  shared/            Dto (dataclass-трансферы) · Port (UnitOfWork, Transaction,
                       MessagePublisher, DuplicateKeyError)
  config/            настройки (yaml + env, get_settings)
  di/                DI-контейнер (композиционный корень)
migrations/          Alembic: payments · payment_outbox · payment_provider_idempotency_store
tests/               integration (testcontainers: БД + очереди) · api
```

## Слои и направление зависимостей

```
worker  →  фасады модулей  →  сервисы (Business)  →  repository / infrastructure
                                                       (за портами из shared/Port)
```

- `worker` — тонкие адаптеры точек входа; зовут только фасады модулей.
- Бизнес-слой (`modules/**/Business`) зависит от **портов** (`shared/Port`), не от
  SQLAlchemy / RabbitMQ / httpx. Конкретные реализации живут в `infrastructure` и
  `repository` и инжектятся через DI.
- `repository` принимает/возвращает **бизнес-сущности** (`repository/entity`), а не ORM:
  ORM-модели и маппинг изолированы в `infrastructure/Persistence`.
- DTO (`shared/Dto`) — `dataclass`-трансферы между слоями; транзакция ходит в
  `ContextTransfer` вместе с DTO.

## Точки входа (`worker/`)

| Процесс | Запуск | Роль |
|---|---|---|
| `api` | `uvicorn worker.api.main:app` | приём `POST`/`GET`, запись платежа+события в БД |
| `consumer` | `faststream run worker.consumer.main:app` | обработка `payments.new`: шлюз → статус → webhook, retry/DLQ |
| `relay` | `python -m worker.relay.main` | докачка `payment_outbox` → `payments.new` |
