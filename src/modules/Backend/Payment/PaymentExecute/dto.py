from dataclasses import dataclass

from repository.entity.payment import Payment
from repository.enum.payment_status import PaymentStatus


@dataclass(slots=True)
class PaymentExecuteTransfer:
    """Загруженный платёж для исполнения во внешнем шлюзе (вход PaymentExecute)."""

    payment: Payment


@dataclass(slots=True)
class ProviderResultTransfer:
    """Результат выполнения платежа провайдером (плагином)."""

    status: PaymentStatus
    provider_ref: str | None = None
    failure_reason: str | None = None
