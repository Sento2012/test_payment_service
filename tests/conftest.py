"""Интеграционный харнесс: реальные Postgres + RabbitMQ (testcontainers).

Один event loop на сессию; схема создаётся из ORM (миграции проверяются отдельно в
Docker e2e); между тестами — TRUNCATE таблиц и purge очередей. Доступы (DATABASE_URL,
RABBITMQ_URL, API_KEY) выставляются в окружение ДО первого обращения к настройкам.
"""
import asyncio
import dataclasses
import json
import os

import pytest
import pytest_asyncio

_TABLES = ("payments", "payment_outbox", "payment_provider_idempotency_store")
_QUEUES = (
    "payments.new",
    "payments.new.retry.1",
    "payments.new.retry.2",
    "payments.new.retry.3",
    "payments.new.dlq",
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def infra():
    """Поднимает Postgres + RabbitMQ и прокидывает доступы в окружение."""
    from testcontainers.postgres import PostgresContainer
    from testcontainers.rabbitmq import RabbitMqContainer

    postgres = PostgresContainer("postgres:16-alpine")
    rabbitmq = RabbitMqContainer("rabbitmq:3.13-management-alpine")
    postgres.start()
    rabbitmq.start()
    try:
        raw_db_url = postgres.get_connection_url()  # postgresql+psycopg2://...
        database_url = (
            raw_db_url.replace("+psycopg2", "+asyncpg").replace("+psycopg", "+asyncpg")
        )
        amqp_url = (
            f"amqp://guest:guest@{rabbitmq.get_container_host_ip()}:"
            f"{rabbitmq.get_exposed_port(5672)}/"
        )
        os.environ["DATABASE_URL"] = database_url
        os.environ["RABBITMQ_URL"] = amqp_url
        os.environ["API_KEY"] = "test-key"

        from config.settings import get_settings

        get_settings.cache_clear()
        yield {"database_url": database_url, "amqp_url": amqp_url}
    finally:
        rabbitmq.stop()
        postgres.stop()


@pytest_asyncio.fixture(scope="session")
async def app_setup(infra):
    """Создаёт схему из ORM, подключает брокер и объявляет топологию (exchange/queues/DLQ)."""
    from infrastructure.Messaging.broker import get_broker
    from infrastructure.Messaging.topology import (
        declare_dlq,
        declare_payments_new_queue,
        declare_retry_queues,
    )
    from infrastructure.Persistence.database import get_engine
    from infrastructure.Persistence.orm import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    broker = get_broker()
    await broker.connect()
    await declare_payments_new_queue(broker)
    await declare_retry_queues(broker)
    await declare_dlq(broker)

    yield
    await broker.close()
    await engine.dispose()


class RabbitProbe:
    """Чтение/очистка очередей с отдельного aio-pika соединения (сторона теста)."""

    def __init__(self, channel) -> None:
        self._channel = channel

    async def purge(self, name: str) -> None:
        queue = await self._channel.get_queue(name, ensure=True)
        await queue.purge()

    async def get_message(self, name: str) -> dict | None:
        queue = await self._channel.get_queue(name, ensure=True)
        message = await queue.get(no_ack=True, fail=False)
        if message is None:
            return None
        return json.loads(message.body.decode())


@pytest_asyncio.fixture(scope="session")
async def rabbit(app_setup):
    import aio_pika

    connection = await aio_pika.connect_robust(os.environ["RABBITMQ_URL"])
    channel = await connection.channel()
    try:
        yield RabbitProbe(channel)
    finally:
        await connection.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_state(app_setup, rabbit):
    """Чистое состояние перед каждым тестом: TRUNCATE таблиц + purge очередей."""
    from sqlalchemy import text

    from infrastructure.Persistence.database import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(text(f"TRUNCATE {', '.join(_TABLES)} CASCADE"))
        await session.commit()
    for queue_name in _QUEUES:
        await rabbit.purge(queue_name)
    yield


class FakeHttpClient:
    """Подменный HTTP-клиент (порт HttpClientInterface): пишет вызовы, по флагу падает."""

    def __init__(self, fail: bool = False) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.fail = fail

    async def post(self, url: str, payload: dict) -> None:
        self.calls.append((url, payload))
        if self.fail:
            raise RuntimeError("webhook delivery failed (emulated)")


@pytest.fixture
def make_container(app_setup):
    """Фабрика DI-контейнера с детерминированным шлюзом (без задержек, заданный исход)."""

    def _make(success_rate: float = 1.0, http_client: FakeHttpClient | None = None):
        from config.groups import GatewaySettings
        from config.settings import get_settings
        from di.container import Container

        settings = dataclasses.replace(
            get_settings(),
            gateway=GatewaySettings(min_delay=0.0, max_delay=0.0, success_rate=success_rate),
        )
        container = Container(settings=settings)
        container._http_client = http_client or FakeHttpClient()
        return container

    return _make


@pytest_asyncio.fixture
async def db(app_setup):
    from infrastructure.Persistence.database import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def api_client(app_setup):
    from httpx import ASGITransport, AsyncClient

    from worker.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client
