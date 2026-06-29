from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from repository.enum.currency import Currency
from repository.enum.payment_status import PaymentStatus
from repository.enum.provider import Provider


@dataclass(slots=True)
class Payment:
    """Бизнес-сущность платежа (соответствует таблице payments).

    Обязательные поля = NOT NULL без БД-дефолта (задаются при создании).
    id/created_at — генерируются БД (None до сохранения). Изменяемая:
    load → mutate → update.
    """

    idempotency_key: str
    amount: Decimal
    currency: Currency
    provider: Provider
    status: PaymentStatus = PaymentStatus.PENDING
    meta: dict = field(default_factory=dict)
    description: str | None = None
    webhook_url: str | None = None
    provider_ref: str | None = None
    failure_reason: str | None = None
    processed_at: datetime | None = None
    notified_at: datetime | None = None
    id: UUID | None = None
    created_at: datetime | None = None
