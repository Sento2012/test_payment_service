# Архитектура — краткий обзор

Основные моменты на один экран. Детали — в [architecture.md](architecture.md) (поток и
решения) и [project-structure.md](project-structure.md) (структура и модули).

## Что это

Три процесса вокруг PostgreSQL + RabbitMQ:

- **api** — принимает `POST/GET`, в одной транзакции пишет платёж и событие в outbox.
- **relay** — докачивает события из outbox в очередь `payments.new`.
- **consumer** — обрабатывает платёж через эмуляцию шлюза и шлёт webhook.

```
POST → [payments + payment_outbox в одной tx] → relay → payments.new → consumer → webhook
```

## Основные моменты реализации

### Outbox pattern

У БД и брокера нет общей транзакции (dual-write). Событие пишется в той же транзакции,
что и платёж; relay надёжно публикует → событие не теряется. Гарантия —
**at-least-once** (возможен дубль, но не потеря).

### Идемпотентность по слоям

Запрос/сообщение может прийти дважды на каждом шаге — на каждой границе своя защита:

| Граница | Проблема | Решение | Код |
|---|---|---|---|
| Клиент → API | повтор `POST` → два платежа | `Idempotency-Key` UNIQUE, повтор возвращает существующий | [orm.py:82](../src/infrastructure/Persistence/orm.py#L82) · [payment_creator.py:36](../src/modules/Backend/Payment/PaymentCreate/payment_creator.py#L36) |
| БД → брокер | dual-write: потеря/«фантом» события | outbox + relay (сначала publish, потом commit) | [outbox_relay.py:39](../src/modules/Backend/Outbox/OutboxRelay/outbox_relay.py#L39) |
| Брокер → consumer | at-least-once: повторная доставка | guard `status` / `notified_at` | [payment_processor.py:68](../src/modules/Backend/Payment/PaymentProcessing/payment_processor.py#L68) · [webhook_notification_sender.py:46](../src/modules/Backend/Notification/webhook_notification_sender.py#L46) |
| Параллельные дубли | prefetch>1 / поды: оба видят `pending` | `SELECT … FOR UPDATE` — второй ждёт и видит не-`pending` | [payment_processor.py:57](../src/modules/Backend/Payment/PaymentProcessing/payment_processor.py#L57) · [payment_repository.py:51](../src/repository/payment_repository.py#L51) |
| Consumer → шлюз | charge прошёл, commit упал → повторное списание | стор результата по `payment.id` в отдельной tx | [payment_executor.py:38](../src/modules/Backend/Payment/PaymentExecute/payment_executor.py#L38) · [store:31](../src/repository/payment_provider_idempotency_store_repository.py#L31) |

**Итог:** событие не теряется, двойного списания нет.

### Retry / DLQ (RabbitMQ-native)

Ошибка доставки → retry-очереди с возрастающим TTL (`1s→5s→25s`) → после 3 попыток →
DLQ. Бизнес-отказ (10%) — не ошибка: `failed`, webhook всё равно уходит.

## Архитектурные принципы

### Модули и сервисы

Вся система собрана из **модулей**: каждая бизнес-область — отдельный модуль, а точки
входа (`worker`: api/consumer/relay) собирают нужные сервисы из DI-контейнера и вызывают
их напрямую. За что отвечает каждый:

| Модуль | Отвечает за |
|---|---|
| **Request** (Frontend) | приём HTTP: роуты, валидация, `X-API-Key` |
| **Payment** | жизненный цикл платежа: создание, обработка через шлюз, чтение |
| **MockPaymentExecute** | эмуляция платёжного шлюза (плагин провайдера) |
| **Notification** | доставка webhook-уведомлений о результате |
| **Outbox** | гарантированная публикация событий (запись + relay) |
| **Idempotency** | защита от повторного списания (стор результата шлюза) |

**Сервис** = класс с одной ответственностью (без фасад-прокси и фабрик: логика прямо в
классе, зависимости инжектятся конструктором в [DI-контейнере](../src/di/container.py)).
**Публичный API** каждого пакета задаётся через `__init__.py` (экспортирует сервис-класс
и его DTO); всё, что не экспортировано, — внутреннее. Импорт через пакет
(`from modules.Backend.Payment.PaymentRepository import PaymentRepositoryService`), а
границы зафиксированы **import-linter** (см. [development.md](development.md)). Польза:
явные границы, заменяемость (новый провайдер/канал = новый сервис), тестируемость.

Как связаны (`──►` — вызывает, справа — зачем):

```
  api → Request → Payment      consumer → Payment      relay → Outbox

  PaymentCreate      ──► Outbox              платёж + событие в одной транзакции
  PaymentProcessing  ──► PaymentExecute      провести платёж через шлюз
                     ──► Notification        отправить webhook о результате
                     ──► PaymentRepository   обновить статус в БД
  PaymentExecute     ──► Idempotency         не списать дважды (дедуп charge)
                     ──► MockPaymentExecute  сам вызов шлюза (plugin)
  OutboxRelay        ──► MessagePublisher    publish → очередь payments.new (порт→адаптер)
```

Полная структура каталогов и сервисы по модулям — в
[project-structure.md](project-structure.md).

### Провайдеры оплаты (плагины)

Платёжные провайдеры подключаются как плагины. `PaymentExecute` объявляет контракт
([provider_execute_plugin_interface.py](../src/modules/Backend/Payment/PaymentExecute/Plugin/provider_execute_plugin_interface.py)),
а конкретный провайдер — отдельный модуль-плагин, реализующий его (сейчас это
`MockPaymentExecute` — эмуляция шлюза). `PaymentExecutor` выбирает подходящий плагин по
`is_applicable` (по `payment.provider`). Новый провайдер = новый плагин с этим
контрактом, регистрируется в DI — без правок существующего кода.

### Чистая архитектура / библиотеконезависимость

Бизнес-слой зависит от **портов** (`shared/Port` + репозиторные интерфейсы), не от
SQLAlchemy / RabbitMQ / httpx; реализации — в `infrastructure`/`repository` и инжектятся
через DI-контейнер (без сторонних библиотек). У домена нет зависимости от `infrastructure`
даже транзитивной (зафиксировано import-linter). Смена ORM/брокера = переписать адаптер,
домен не трогается.

### Транзакции

Порт `UnitOfWork` + `ContextTransfer`: короткие транзакции вокруг DB-операций, долгие
вызовы (шлюз, webhook) — между ними, без удержания соединения.
