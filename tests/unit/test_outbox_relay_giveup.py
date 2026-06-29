"""OutboxRelay: «ядовитое» событие после max_attempts паркуется в FAILED, а не
ретраится вечно. Юнит-тест с фейками (без БД/брокера)."""
from uuid import uuid4

from config.groups import RelaySettings
from modules.Backend.Outbox.OutboxRelay.outbox_relay import OutboxRelay
from repository.entity.outbox_event import OutboxEvent
from repository.enum.event_type import EventType
from repository.enum.outbox_status import OutboxStatus


class _FakeTx:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *exc):
        return False


class _FakeUnitOfWork:
    def begin(self):
        return _FakeTx()


class _FakeRepositoryFacade:
    def __init__(self, events: list[OutboxEvent]) -> None:
        self._events = events

    async def get_pending_events_with_lock(self, _transfer):
        return self._events

    async def update_outbox_event(self, _transfer):
        return None


class _FailingRabbitMqFacade:
    async def publish_event(self, _transfer):
        raise RuntimeError("broker down")


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
        _FakeUnitOfWork(), _FakeRepositoryFacade(events), _FailingRabbitMqFacade(), settings
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
