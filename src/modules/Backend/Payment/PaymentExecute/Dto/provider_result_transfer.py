from dataclasses import dataclass

from repository.enum.payment_status import PaymentStatus


@dataclass(slots=True)
class ProviderResultTransfer:
    """Результат выполнения платежа провайдером (плагином)."""

    status: PaymentStatus
    provider_ref: str | None = None
    failure_reason: str | None = None
