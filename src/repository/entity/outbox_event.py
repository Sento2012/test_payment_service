from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from repository.enum.event_type import EventType
from repository.enum.outbox_status import OutboxStatus


@dataclass(slots=True)
class OutboxEvent:
    """Бизнес-сущность события outbox (соответствует таблице payment_outbox).

    Обязательные поля = NOT NULL без БД-дефолта. Идентичность задаёт домен: id/created_at
    генерируются при создании (created_at — источник истины БД, подставляется при чтении).
    published_at/available_at — поля жизненного цикла (None до публикации/планирования).
    Изменяемая: load → mutate → update.
    """

    event_type: EventType
    routing_key: str
    payment_id: UUID
    payload: dict
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
