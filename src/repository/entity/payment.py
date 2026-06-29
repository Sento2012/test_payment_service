from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from repository.enum.currency import Currency
from repository.enum.payment_status import PaymentStatus
from repository.enum.provider import Provider


@dataclass(slots=True)
class Payment:
    """Бизнес-сущность платежа (соответствует таблице payments).

    Обязательные поля = NOT NULL без БД-дефолта (задаются при создании).
    Идентичность задаётся доменом: id генерируется сразу (uuid4), created_at получает
    значение в момент создания. Источник истины created_at — БД: при чтении _to_entity
    подставляет фактическое значение колонки. Изменяемая: load → mutate → update.
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
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
