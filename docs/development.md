# Локальная разработка

## Без Docker для приложения (инфраструктура в Docker)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
docker compose up -d postgres rabbitmq          # только инфраструктура
export DATABASE_URL=postgresql+asyncpg://payments:payments@localhost:5432/payments
export RABBITMQ_URL=amqp://guest:guest@localhost:5672/
export API_KEY=secret-api-key
alembic upgrade head
uvicorn worker.api.main:app --reload            # API
faststream run worker.consumer.main:app         # consumer
python -m worker.relay.main                     # relay
```

> `DATABASE_URL`/`RABBITMQ_URL` указывают на проброшенные наружу порты Postgres/RabbitMQ.
> В compose наружу публикуется только Traefik, поэтому для локального запуска приложения
> порты БД/брокера нужно временно пробросить (или поднимать всё через `docker compose up`).

## Качество кода (линт · типы · границы)

Конфиг всех инструментов — в `pyproject.toml`; зависимости — в `requirements-dev.txt`.
Удобные цели в `Makefile`:

```bash
make lint      # ruff: статический линт (E,W,F,I,UP,B,SIM,C4)
make format    # ruff format + авто-фиксы
make type      # mypy: статическая типизация
make imports   # import-linter: контроль архитектурных границ
make test      # pytest (integration на testcontainers)
make check     # всё сразу — lint + type + imports + test
```

- **ruff** — линтер/форматтер (isort-импорты, pyupgrade, bugbear …).
- **mypy** — статическая типизация (`check_untyped_defs`, `no_implicit_optional`).
- **import-linter** — фиксирует границы слоёв (контракты в `pyproject.toml`):
  `shared` и `config` не зависят от прикладных слоёв; Backend-домен не зависит от
  `infrastructure`/presentation/composition (зависит только от портов — `shared/Port` +
  репозиторные интерфейсы); `infrastructure` не зависит от `modules`/composition.

## Тесты

Интеграционные на **testcontainers** (реальные Postgres + RabbitMQ): проверяют бизнес-
процессы сквозь БД и очереди + API. Нужен запущенный Docker.

```bash
pip install -r requirements-dev.txt
pytest
```

Как устроен харнесс (`tests/conftest.py`):

- поднимает контейнеры Postgres + RabbitMQ, прокидывает доступы в окружение **до**
  первого обращения к настройкам;
- схема создаётся из ORM (`Base.metadata.create_all`) — миграции проверяются отдельно в
  Docker e2e; между тестами `TRUNCATE` таблиц + purge очередей;
- DI-контейнер с детерминированным шлюзом (без задержек, заданный success-rate) и
  подменным HTTP-клиентом (порт `HttpClientInterface`); отдельный aio-pika probe читает
  очереди для проверки публикаций.

| Файл | Что проверяет |
|---|---|
| `tests/integration/test_payment_create_service.py` | атомарная запись `payment + payment_outbox`, идемпотентность по ключу |
| `tests/integration/test_outbox_relay_service.py` | relay публикует в `payments.new`, помечает событие `published` |
| `tests/integration/test_payment_processing_service.py` | обработка через шлюз (success/failed), статус+webhook в БД, ошибка webhook → retry, повторная обработка идемпотентна |
| `tests/integration/test_consumer_retry_dlq.py` | роутинг ошибок: retry-очередь уровня → DLQ |
| `tests/unit/test_outbox_relay_giveup.py` | «ядовитое» событие → `FAILED` после `max_attempts` (без БД/брокера) |
| `tests/api/test_payments_api.py` | POST 202 / GET, `X-API-Key` (401), `Idempotency-Key` (422), идемпотентность, 404 |
| `tests/api/test_payments_validation.py` | валидация кривого ввода → 422 (вкл. SSRF `webhook_url`) |
