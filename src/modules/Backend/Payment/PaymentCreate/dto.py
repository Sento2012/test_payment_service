from dataclasses import dataclass, field
from decimal import Decimal

from repository.enum.currency import Currency
from repository.enum.provider import DEFAULT_PROVIDER, Provider
from shared.Dto import ContextTransfer


@dataclass(slots=True)
class PaymentDraftTransfer:
    """Входные данные для создания платежа (из API + idempotency key)."""

    idempotency_key: str
    amount: Decimal
    currency: Currency
    webhook_url: str | None = None
    description: str | None = None
    meta: dict = field(default_factory=dict)
    provider: Provider = DEFAULT_PROVIDER
    context: ContextTransfer = field(default_factory=ContextTransfer)
