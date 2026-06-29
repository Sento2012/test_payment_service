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
| Клиент → API | повтор `POST` → два платежа | `Idempotency-Key` UNIQUE, повтор возвращает существующий | [orm.py:81](../src/infrastructure/Persistence/orm.py#L81) · [payment_creator.py:66](../src/modules/Backend/Payment/PaymentCreate/Business/payment_creator.py#L66) |
| БД → брокер | dual-write: потеря/«фантом» события | outbox + relay (сначала publish, потом commit) | [outbox_relay.py:59](../src/modules/Backend/Outbox/OutboxRelay/Business/outbox_relay.py#L59) |
| Брокер → consumer | at-least-once: повторная доставка | guard `status` / `notified_at` | [payment_processor.py:69](../src/modules/Backend/Payment/PaymentProcessing/Business/payment_processor.py#L69) · [webhook_notification_sender.py:63](../src/modules/Backend/Notification/WebhookNotificationService/Business/webhook_notification_sender.py#L63) |
| Параллельные дубли | prefetch>1 / поды: оба видят `pending` | `SELECT … FOR UPDATE` — второй ждёт и видит не-`pending` | [payment_processor.py:52](../src/modules/Backend/Payment/PaymentProcessing/Business/payment_processor.py#L52) · [payment_repository.py:63](../src/repository/payment_repository.py#L63) |
| Consumer → шлюз | charge прошёл, commit упал → повторное списание | стор результата по `payment.id` в отдельной tx | [payment_executor.py:46](../src/modules/Backend/Payment/PaymentExecute/Business/payment_executor.py#L46) · [store:29](../src/repository/payment_provider_idempotency_store_repository.py#L29) |

**Итог:** событие не теряется, двойного списания нет.

### Retry / DLQ (RabbitMQ-native)

Ошибка доставки → retry-очереди с возрастающим TTL (`1s→5s→25s`) → после 3 попыток →
DLQ. Бизнес-отказ (10%) — не ошибка: `failed`, webhook всё равно уходит.

## Архитектурные принципы

### Модули и сервисы

Вся система собрана из **модулей**: каждая бизнес-область — отдельный модуль, а точки
входа (`worker`: api/consumer/relay) лишь вызывают их фасады. За что отвечает каждый:

| Модуль | Отвечает за |
|---|---|
| **Request** (Frontend) | приём HTTP: роуты, валидация, `X-API-Key` |
| **Payment** | жизненный цикл платежа: создание, обработка через шлюз, чтение |
| **MockPaymentExecute** | эмуляция платёжного шлюза (плагин провайдера) |
| **Notification** | доставка webhook-уведомлений о результате |
| **Outbox** | гарантированная публикация событий (запись + relay) |
| **Idempotency** | защита от повторного списания (стор результата шлюза) |
| **RabbitMq** | публикация сообщений в брокер |

**Модуль** = фасад-точка входа (только проксирует; модули общаются лишь через фасады
друг друга) + **сервисы**. **Сервис** = одна ответственность (`facade · factory ·
Business`). Польза: явные границы, заменяемость (новый провайдер/канал = новый сервис),
тестируемость.

Как связаны (`──►` — вызывает, справа — зачем):

```
  api → Request → Payment      consumer → Payment      relay → Outbox

  PaymentCreate      ──► Outbox              платёж + событие в одной транзакции
  PaymentProcessing  ──► PaymentExecute      провести платёж через шлюз
                     ──► Notification        отправить webhook о результате
                     ──► PaymentRepository   обновить статус в БД
  PaymentExecute     ──► Idempotency         не списать дважды (дедуп charge)
                     ──► MockPaymentExecute  сам вызов шлюза (plugin)
  OutboxRelay        ──► RabbitMq            publish → очередь payments.new
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

Бизнес-слой зависит от **портов** (`shared/Port`), не от SQLAlchemy / RabbitMQ / httpx;
реализации — в `infrastructure` и инжектятся через DI-контейнер (без сторонних
библиотек). Смена ORM/брокера = переписать адаптер, домен не трогается.

### Транзакции

Порт `UnitOfWork` + `ContextTransfer`: короткие транзакции вокруг DB-операций, долгие
вызовы (шлюз, webhook) — между ними, без удержания соединения.
