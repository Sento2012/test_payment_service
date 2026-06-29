from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from repository.enum.currency import Currency
from repository.enum.payment_status import PaymentStatus
from repository.enum.provider import DEFAULT_PROVIDER, Provider

Amount = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]


class CreatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Amount
    currency: Currency
    description: str | None = Field(default=None, max_length=1024)
    metadata: dict = Field(default_factory=dict)
    webhook_url: str | None = Field(default=None, max_length=2048)
    provider: Provider = DEFAULT_PROVIDER


class PaymentCreatedResponse(BaseModel):
    """Ответ 202 Accepted на создание платежа."""

    payment_id: UUID
    status: PaymentStatus
    created_at: datetime


class PaymentResponse(BaseModel):
    """Детальная информация о платеже (GET)."""

    payment_id: UUID
    amount: Decimal
    currency: Currency
    status: PaymentStatus
    description: str | None
    metadata: dict
    webhook_url: str | None
    provider: Provider
    provider_ref: str | None
    failure_reason: str | None
    created_at: datetime
    processed_at: datetime | None
    notified_at: datetime | None
