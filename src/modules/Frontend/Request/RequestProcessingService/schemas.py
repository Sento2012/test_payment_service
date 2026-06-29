import ipaddress
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from repository.enum.currency import Currency
from repository.enum.payment_status import PaymentStatus
from repository.enum.provider import DEFAULT_PROVIDER, Provider

Amount = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]


def _ensure_safe_webhook_url(url: str) -> str:
    """Защита от SSRF: только https и не приватный/служебный хост (literal-IP).

    DNS-rebinding (хост резолвится в приватный IP в момент отправки) — вне области
    валидации схемы; при ужесточении решается резолвом+пином IP на стороне клиента.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("webhook_url must use https")
    host = parsed.hostname
    if not host:
        raise ValueError("webhook_url must contain a host")
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("webhook_url host is not allowed")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None  # не литеральный IP — пропускаем
    if ip is not None and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise ValueError("webhook_url must not point to a private/reserved address")
    return url


class CreatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Amount
    currency: Currency
    description: str | None = Field(default=None, max_length=1024)
    metadata: dict = Field(default_factory=dict)
    webhook_url: str | None = Field(default=None, max_length=2048)
    provider: Provider = DEFAULT_PROVIDER

    @field_validator("webhook_url")
    @classmethod
    def _validate_webhook_url(cls, value: str | None) -> str | None:
        return _ensure_safe_webhook_url(value) if value else value


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
