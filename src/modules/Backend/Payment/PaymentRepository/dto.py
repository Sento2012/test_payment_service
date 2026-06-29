from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from repository.entity.payment import Payment
from repository.enum.currency import Currency
from repository.enum.provider import DEFAULT_PROVIDER, Provider
from shared.Dto import ContextTransfer


@dataclass(slots=True)
class PaymentFindTransfer:
    """Условия чтения платежа (фильтры) — вход find_payment."""

    payment_id: UUID | None = None
    idempotency_key: str | None = None
    # SELECT ... FOR UPDATE — захватить row-lock (для атомарной обработки в consumer'е)
    for_update: bool = False
    context: ContextTransfer = field(default_factory=ContextTransfer)


@dataclass(slots=True)
class PaymentCreateTransfer:
    """Данные для записи нового платежа — вход create_payment.

    Собственный DTO репозитория: модуль создания (PaymentCreate) маппит свой
    PaymentDraftTransfer сюда, репозиторий не зависит от чужих DTO."""

    idempotency_key: str
    amount: Decimal
    currency: Currency
    webhook_url: str | None = None
    description: str | None = None
    meta: dict = field(default_factory=dict)
    provider: Provider = DEFAULT_PROVIDER
    context: ContextTransfer = field(default_factory=ContextTransfer)


@dataclass(slots=True)
class PaymentUpdateTransfer:
    """Изменённая сущность платежа для сохранения (load → mutate → update),
    + контекст с (необязательной) транзакцией — вход update_payment."""

    payment: Payment
    context: ContextTransfer = field(default_factory=ContextTransfer)
