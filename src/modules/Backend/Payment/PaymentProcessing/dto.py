from dataclasses import dataclass, field
from uuid import UUID

from shared.Dto import ContextTransfer


@dataclass(slots=True)
class PaymentReferenceTransfer:
    """Ссылка на платёж по id (+ контекст). Вход операций обработки."""

    payment_id: UUID
    context: ContextTransfer = field(default_factory=ContextTransfer)
