from dataclasses import dataclass, field
from uuid import UUID

from repository.entity.outbox_event import OutboxEvent
from repository.enum.event_type import EventType
from shared.Dto import ContextTransfer


@dataclass(slots=True)
class OutboxEventDraftTransfer:
    """Событие, которое пишется в outbox в одной транзакции с агрегатом."""

    event_type: EventType
    routing_key: str
    payment_id: UUID
    payload: dict
    context: ContextTransfer = field(default_factory=ContextTransfer)


@dataclass(slots=True)
class GetPendingEventsWithLockTransfer:
    """Запрос пачки pending-событий relay'ем (+ контекст с транзакцией relay)."""

    limit: int
    context: ContextTransfer = field(default_factory=ContextTransfer)


@dataclass(slots=True)
class OutboxEventUpdateTransfer:
    """Изменённое событие outbox для сохранения (load → mutate → update),
    + контекст с транзакцией relay для записи в той же tx."""

    outbox_event: OutboxEvent
    context: ContextTransfer = field(default_factory=ContextTransfer)
