from dataclasses import dataclass, field
from uuid import UUID

from repository.entity.payment import Payment
from shared.Dto.context_transfer import ContextTransfer


@dataclass(slots=True)
class PaymentConditionsTransfer:
    """Условия чтения платежа (фильтры) — общий вход find_payment."""

    payment_id: UUID | None = None
    idempotency_key: str | None = None
    # SELECT ... FOR UPDATE — захватить row-lock (для атомарной обработки в consumer'е)
    for_update: bool = False
    context: ContextTransfer = field(default_factory=ContextTransfer)


@dataclass(slots=True)
class PaymentUpdateTransfer:
    """Изменённая сущность платежа для сохранения (load → mutate → update),
    + контекст с (необязательной) транзакцией."""

    payment: Payment
    context: ContextTransfer = field(default_factory=ContextTransfer)
