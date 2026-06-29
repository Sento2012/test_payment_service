from abc import ABC, abstractmethod
from uuid import UUID

from repository.entity.payment import Payment
from shared.Port import Transaction


class PaymentRepositoryInterface(ABC):
    """Порт персистентности платежей. Домен зависит от этой абстракции; конкретная
    реализация (SQLAlchemy) живёт в repository и инжектится через DI."""

    @abstractmethod
    async def create(self, transaction: Transaction, payment: Payment) -> Payment: ...

    @abstractmethod
    async def find(
        self,
        transaction: Transaction,
        payment_id: UUID | None = None,
        idempotency_key: str | None = None,
        for_update: bool = False,
    ) -> Payment | None: ...

    @abstractmethod
    async def update(self, transaction: Transaction, payment: Payment) -> None: ...
