from abc import ABC, abstractmethod

from repository.entity.outbox_event import OutboxEvent
from shared.Port import Transaction


class OutboxRepositoryInterface(ABC):
    """Порт персистентности payment_outbox. Домен зависит от абстракции; конкретная
    реализация (SQLAlchemy) живёт в repository и инжектится через DI."""

    @abstractmethod
    async def create(
        self, transaction: Transaction, outbox_event: OutboxEvent
    ) -> OutboxEvent: ...

    @abstractmethod
    async def get_pending_events_with_lock(
        self, transaction: Transaction, limit: int
    ) -> list[OutboxEvent]: ...

    @abstractmethod
    async def update(
        self, transaction: Transaction, outbox_event: OutboxEvent
    ) -> None: ...
