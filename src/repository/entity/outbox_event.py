from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from repository.enum.event_type import EventType
from repository.enum.outbox_status import OutboxStatus


@dataclass(slots=True)
class OutboxEvent:
    """Бизнес-сущность события outbox (соответствует таблице payment_outbox).

    Обязательные поля = NOT NULL без БД-дефолта. id/available_at/created_at —
    генерируются БД (None до сохранения). Изменяемая: load → mutate → update.
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
    id: UUID | None = None
    created_at: datetime | None = None
