# Асинхронный сервис процессинга платежей

Принимает запросы на оплату, асинхронно обрабатывает их через эмуляцию платёжного
шлюза и уведомляет клиента о результате через webhook. Гарантированная публикация
событий — **Outbox pattern**, доставка — **at-least-once** с **retry + DLQ** на RabbitMQ.

**Стек:** FastAPI · Pydantic v2 · SQLAlchemy 2.0 (async) · PostgreSQL · RabbitMQ
(FastStream) · Alembic · Docker Compose · Traefik.

## Ревьюеру

Спасибо, что согласились посмотреть проект. Заранее понимаю, что для тестового задания
это местами выглядит как оверинженеринг. Хотелось сделать сервис со **слабой
связанностью с инфраструктурой, расширяемым и удобным в сопровождении**, опираясь на основные приёмы
популярных подходов — Clean Architecture / layered architecture / DDD, — поэтому проект
получился несколько шире, чем минимально достаточный. Чтобы это не мешало ревью, я
подготовил краткую документацию — начать удобнее всего с
**[обзора архитектуры и бизнес-логики на один экран](docs/overview.md)**.

## Документация

- [docs/overview.md](docs/overview.md) — **краткий обзор
  архитектуры и бизнес-логики** (основные моменты на один экран).
- [docs/architecture.md](docs/architecture.md) — поток обработки, Outbox, транзакции,
  идемпотентность по слоям, retry/DLQ.
- [docs/project-structure.md](docs/project-structure.md) — структура проекта: модули/
  сервисы, публичный API пакетов через `__init__`, слои и зависимости.
- [docs/development.md](docs/development.md) — локальный запуск без Docker, тесты и
  quality gate (ruff · mypy · import-linter).

---

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Поднимутся `traefik`, `postgres`, `rabbitmq`, `migrate` (разовая миграция), `api`,
`consumer`, `relay`. Наружу торчит **только Traefik** (порт `TRAEFIK_HTTP_PORT`, по
умолчанию `8088`; при конфликте — `TRAEFIK_HTTP_PORT=9090 docker compose up`).

| URL (`*.localhost` → 127.0.0.1) | Что |
|---|---|
| http://api.payments.localhost:8088/docs | API + Swagger |
| http://rabbitmq.payments.localhost:8088 | RabbitMQ Management (guest/guest) |
| http://traefik.payments.localhost:8088 | Traefik dashboard |

### Примеры

Все эндпоинты требуют `X-API-Key` (из `.env`, по умолчанию `secret-api-key`).

```bash
# создать платёж → 202 Accepted {payment_id, status, created_at}
curl -i -X POST http://api.payments.localhost:8088/api/v1/payments \
  -H "X-API-Key: secret-api-key" \
  -H "Idempotency-Key: order-42" \
  -H "Content-Type: application/json" \
  -d '{"amount":"199.90","currency":"RUB","metadata":{"user_id":7},
       "webhook_url":"https://webhook.site/<your-uuid>"}'

# получить платёж (через 2–5с станет succeeded/failed)
curl http://api.payments.localhost:8088/api/v1/payments/<payment_id> \
  -H "X-API-Key: secret-api-key"
```

`POST` обязательно требует заголовок `Idempotency-Key`; повтор с тем же ключом
возвращает тот же платёж, нового не создаёт.

### Смоук-тест API

Готовый скрипт: создание → идемпотентность → ожидание статуса + негативные кейсы
(401/422/404).

```bash
./scripts/api_smoke.sh
# переопределение: BASE_URL=... API_KEY=... WEBHOOK_URL=https://webhook.site/<uuid> ./scripts/api_smoke.sh
```

## Тесты

Интеграционные на testcontainers (реальные Postgres + RabbitMQ) + API. Запуск, покрытие
и устройство харнесса — в [docs/development.md](docs/development.md).

## Конфигурация

- **Доступы/секреты — через env** ([.env.example](.env.example)): `DATABASE_URL`,
  `RABBITMQ_URL`, `API_KEY` (+ `POSTGRES_*`, `TRAEFIK_HTTP_PORT`).
- **Прикладные параметры — в [src/config/config.yaml](src/config/config.yaml)**:
  `prefetch`, `relay.*`, `retry.ttls_ms`, `webhook.timeout`, `gateway.*`.

Сборка — `get_settings()` ([src/config/settings.py](src/config/settings.py)): читается
`config.yaml`, поверх — доступы из env.
