from abc import ABC, abstractmethod

from repository.entity.idempotency_record import IdempotencyRecord
from shared.Port import Transaction


class PaymentProviderIdempotencyStoreRepositoryInterface(ABC):
    """Порт стора идемпотентности charge. Домен зависит от абстракции; конкретная
    реализация (SQLAlchemy) живёт в repository и инжектится через DI."""

    @abstractmethod
    async def find(
        self, transaction: Transaction, key: str
    ) -> IdempotencyRecord | None: ...

    @abstractmethod
    async def get_or_create(
        self, transaction: Transaction, idempotency_record: IdempotencyRecord
    ) -> IdempotencyRecord: ...
