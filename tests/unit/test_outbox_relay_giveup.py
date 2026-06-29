"""OutboxRelay: «ядовитое» событие после max_attempts паркуется в FAILED, а не
ретраится вечно. Юнит-тест с фейками (без БД/брокера)."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from config.groups import RelaySettings
from modules.Backend.Outbox.OutboxRelay.outbox_relay import OutboxRelay
from repository.entity.outbox_event import OutboxEvent
from repository.enum.event_type import EventType
from repository.enum.outbox_status import OutboxStatus
from shared.Dto import PublishEventTransfer, PublishToQueueTransfer
from shared.Port import MessagePublisher, Transaction


class _FakeUnitOfWork:
    """Реализует порт UnitOfWork; хэндл не используется (репозиторий замокан)."""

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[Transaction]:
        yield object()

    @asynccontextmanager
    async def use_transaction(self, context_transfer=None) -> AsyncIterator[Transaction]:
        yield object()


class _FakeOutboxRepositoryService:
    def __init__(self, events: list[OutboxEvent]) -> None:
        self._events = events

    async def get_pending_events_with_lock(self, _transfer) -> list[OutboxEvent]:
        return self._events

    async def update_outbox_event(self, _transfer) -> None:
        return None


class _FailingPublisher(MessagePublisher):
    async def publish_event(self, publish_event_transfer: PublishEventTransfer) -> None:
        raise RuntimeError("broker down")

    async def publish_to_queue(
        self, publish_to_queue_transfer: PublishToQueueTransfer
    ) -> None:
        raise NotImplementedError  # в этом тесте не используется


def _event(attempts: int) -> OutboxEvent:
    return OutboxEvent(
        event_type=EventType.PAYMENT_NEW,
        routing_key="payments.new",
        payment_id=uuid4(),
        payload={"payment_id": str(uuid4())},
        attempts=attempts,
    )


def _relay(events: list[OutboxEvent], max_attempts: int = 3) -> OutboxRelay:
    settings = RelaySettings(
        batch_size=10,
        poll_interval=1.0,
        backoff_base=2.0,
        backoff_cap=60.0,
        max_attempts=max_attempts,
    )
    return OutboxRelay(
        _FakeUnitOfWork(),
        # тест-дубль доменного сервиса (конкретный класс) — порт для него не заводим
        _FakeOutboxRepositoryService(events),  # type: ignore[arg-type]
        _FailingPublisher(),
        settings,
    )


async def test_parked_as_failed_after_max_attempts():
    event = _event(attempts=2)  # max_attempts - 1: следующая неудача исчерпает лимит
    await _relay([event], max_attempts=3).relay_pending_events()

    assert event.attempts == 3
    assert event.status == OutboxStatus.FAILED


async def test_still_pending_before_max_attempts():
    event = _event(attempts=0)
    await _relay([event], max_attempts=3).relay_pending_events()

    assert event.attempts == 1
    assert event.status == OutboxStatus.PENDING  # ещё в ретраях, не запаркован
