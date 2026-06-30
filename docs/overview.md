# Архитектура — краткий обзор

Основные моменты на один экран. Гарантии и защиты (outbox, идемпотентность, retry/DLQ) —
в [implementation-notes.md](implementation-notes.md). Детали — в
[architecture.md](architecture.md) (поток и решения) и
[project-structure.md](project-structure.md) (структура и модули).

## Что это

Три процесса вокруг PostgreSQL + RabbitMQ:

- **api** ([main.py](../src/worker/api/main.py)) — принимает `POST/GET`, в одной транзакции пишет платёж и событие в outbox.
- **relay** ([main.py](../src/worker/relay/main.py)) — докачивает события из outbox в очередь `payments.new`.
- **consumer** ([main.py](../src/worker/consumer/main.py)) — обрабатывает платёж через эмуляцию шлюза и шлёт webhook.

```
POST → [payments + payment_outbox в одной tx] → relay → payments.new → consumer → webhook
```

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

**Сервис** = класс с одной ответственностью: логика прямо в классе, зависимости
инжектятся через конструктор в [DI-контейнере](../src/di/container.py).
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
