# Архитектура

Поток обработки, гарантии и ключевые инженерные решения. Структура кода и иерархия
модулей — в [project-structure.md](project-structure.md).

## Поток обработки

```
POST /api/v1/payments  (X-API-Key, Idempotency-Key)
  └─ PaymentCreate: [одна tx] INSERT payments(pending) + INSERT payment_outbox(pending) → 202

relay (отдельный процесс, поллит outbox)
  └─ SELECT outbox WHERE pending FOR UPDATE SKIP LOCKED → publish(payments.new) → mark published

consumer (payments.new, prefetch=N) — одно действие process_payment:
  ├─ [tx, FOR UPDATE] SELECT payment → шлюз 2–5с (90% ok / 10% fail) → UPDATE status → commit (лок снят)
  └─ webhook (модуль Notification, своя короткая tx) → UPDATE notified_at
     ошибка доставки → retry (TTL 1s→5s→25s) → после 3 попыток → DLQ
```

## Outbox pattern

У БД и брокера нет общей транзакции — это **dual-write problem**: если писать в БД и
публиковать в брокер по отдельности, при сбое между ними событие либо теряется, либо
становится «фантомным». Решение: `payment` и событие пишутся в **одной** транзакции в
таблицу `payment_outbox`, а отдельный процесс **relay** надёжно докачивает события в
брокер (`SELECT … FOR UPDATE SKIP LOCKED` → publish → mark published). Так событие не
теряется, а несколько relay-инстансов делят очередь без дублей.

Порядок в relay намеренный: **сначала publish, потом commit статуса**. При сбое после
publish строка остаётся `pending` и будет опубликована повторно — это **at-least-once**
(возможен дубль, но не потеря). Дубли гасит идемпотентность (ниже).

«Ядовитое» событие (публикация стабильно падает) не ретраится вечно: после
`relay.max_attempts` неудач оно паркуется в статус `FAILED` (с `last_error`) — из выборки
pending больше не берётся, требует разбора/алерта.

## Транзакции и изоляция от ORM

- Порт `UnitOfWork` (`shared/Port/persistence.py`) инжектится в сервисы. Транзакция
  едет в `ContextTransfer` вместе с DTO: репозиторий через `use_transaction` работает в
  транзакции из контекста (**enlisted**), либо открывает свою короткую, если контекст пуст.
- Долгие операции (шлюз 2–5с, webhook) выполняются **между** короткими транзакциями —
  соединение из пула не удерживается на время сетевых вызовов.
- Атомарная запись `payment + payment_outbox`: `PaymentCreate` открывает транзакцию,
  кладёт её в `context`, оба INSERT идут в ней.
- Бизнес-слой не знает про SQLAlchemy: `UnitOfWork.begin()` отдаёт непрозрачный
  `Transaction`-хэндл, нарушение уникальности приходит доменным `DuplicateKeyError`
  (не `IntegrityError`). Маппинг — единственное место в `infrastructure/Persistence`.
  Смена ORM = переписать адаптеры в `infrastructure`, домен не трогается.

## Идемпотентность — по слоям

Каждая граница в распределённой системе — отдельная at-least-once граница, и у каждой
свой механизм дедупликации:

| Граница | Механизм | От чего защищает |
|---|---|---|
| client → API | `Idempotency-Key` (UNIQUE на `payments`) | дубль **запроса на создание** |
| DB → брокер | Outbox + relay | потеря/фантом **события** |
| брокер → consumer (повтор) | guard `status=pending` / `notified_at` | дубль **доставки сообщения** |
| конкурентные дубли в consumer | `SELECT … FOR UPDATE` на платеже | двойная обработка одного платежа |
| consumer → шлюз | стор по `payment.id` (`payment_provider_idempotency_store`) | повторный **charge** при краше до commit |

Последние три закрывают разные дыры одной зоны (двойное списание):

- **`status=pending` guard** — ловит повтор, когда первая обработка уже завершилась и
  закоммитилась.
- **`FOR UPDATE`** — ловит конкурентные дубли (prefetch > 1, несколько подов): дубль
  ждёт на локе, после commit видит не-`pending` и пропускает. Лок снимается до сетевого
  вызова webhook. Crash-safe: краш → rollback → строка снова `pending` → переобработка.
- **Стор шлюза** — единственная защита от случая «charge прошёл, но commit статуса
  упал/краш»: результат сохраняется по ключу `payment.id` в **отдельной** транзакции
  (переживает откат платёжной), повторный вызов возвращает сохранённый результат без
  нового списания. Стор в Postgres → общий для всех подов consumer'а.

## Retry / DLQ (RabbitMQ-native)

`payments.new` обрабатывается consumer'ом. При ошибке доставки (например, недоступен
webhook) сообщение перекладывается в retry-очередь уровня с возрастающим TTL
(`retry.ttls_ms`, по умолчанию `1s → 5s → 25s`); по истечении TTL dead-letter возвращает
его в основной обменник. После исчерпания попыток → `payments.new.dlq`.

Бизнес-отказ оплаты (10%) — это **не** ошибка обработки: платёж получает `status=failed`,
webhook всё равно отправляется (уведомляем клиента о результате — и success, и failed).

Очереди (видно в RabbitMQ Management): `payments.new`, `payments.new.retry.{1,2,3}`,
`payments.new.dlq`.

## Валидация webhook_url (SSRF)

`webhook_url` приходит от клиента, а сервис сам делает на него POST из consumer'а —
потенциальный **SSRF**. На входе (Pydantic-схема) требуем `https` и запрещаем
приватные/служебные адреса (`localhost`, literal-IP из private/loopback/link-local/
reserved диапазонов, напр. `169.254.169.254`). Остаточный риск — DNS-rebinding (хост
резолвится в приватный IP в момент отправки); закрывается резолвом+пином IP в
HTTP-клиенте при необходимости.
