# Основные тонкости реализации

Ключевые гарантии и защиты на один экран. Поток обработки и детали решений —
в [architecture.md](architecture.md).

## Outbox pattern

У БД и брокера нет общей транзакции (dual-write). Событие пишется в той же транзакции,
что и платёж; relay надёжно публикует → событие не теряется. Гарантия —
**at-least-once** (возможен дубль, но не потеря).

## Идемпотентность по слоям

Запрос/сообщение может прийти дважды на каждом шаге — на каждой границе своя защита:

| Граница | Проблема | Решение | Код |
|---|---|---|---|
| Клиент → API | повтор `POST` → два платежа | `Idempotency-Key` UNIQUE, повтор возвращает существующий | [orm.py:82](../src/infrastructure/Persistence/orm.py#L82) · [payment_creator.py:36](../src/modules/Backend/Payment/PaymentCreate/payment_creator.py#L36) |
| БД → брокер | dual-write: потеря/«фантом» события | outbox + relay (сначала publish, потом commit) | [outbox_relay.py:39](../src/modules/Backend/Outbox/OutboxRelay/outbox_relay.py#L39) |
| Брокер → consumer | at-least-once: повторная доставка | guard `status` / `notified_at` | [payment_processor.py:68](../src/modules/Backend/Payment/PaymentProcessing/payment_processor.py#L68) · [webhook_notification_sender.py:46](../src/modules/Backend/Notification/webhook_notification_sender.py#L46) |
| Параллельные дубли | prefetch>1 / поды: оба видят `pending` | `SELECT … FOR UPDATE` — второй ждёт и видит не-`pending` | [payment_processor.py:57](../src/modules/Backend/Payment/PaymentProcessing/payment_processor.py#L57) · [payment_repository.py:51](../src/repository/payment_repository.py#L51) |
| Consumer → шлюз | charge прошёл, commit упал → повторное списание | стор результата по `payment.id` в отдельной tx | [payment_executor.py:38](../src/modules/Backend/Payment/PaymentExecute/payment_executor.py#L38) · [store:31](../src/repository/payment_provider_idempotency_store_repository.py#L31) |

**Итог:** событие не теряется, двойного списания нет.

## Retry / DLQ (RabbitMQ-native)

Ошибка доставки → retry-очереди с возрастающим TTL (`1s→5s→25s`) → после 3 попыток →
DLQ. Бизнес-отказ (10%) — не ошибка: `failed`, webhook всё равно уходит.
