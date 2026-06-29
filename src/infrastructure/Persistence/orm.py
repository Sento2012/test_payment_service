from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from repository.enum.currency import Currency
from repository.enum.outbox_status import OutboxStatus
from repository.enum.payment_status import PaymentStatus
from repository.enum.provider import Provider
from repository.enum.event_type import EventType


def _pg_enum(py_enum, name: str) -> Enum:
    # values_callable -> в БД пишутся value ("pending"), а не имена членов ("PENDING").
    return Enum(
        py_enum,
        name=name,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
    )


_PAYMENT_STATUS_ENUM = _pg_enum(PaymentStatus, "payment_status")
_CURRENCY_ENUM = _pg_enum(Currency, "currency")
_PROVIDER_ENUM = _pg_enum(Provider, "provider")
_OUTBOX_STATUS_ENUM = _pg_enum(OutboxStatus, "outbox_status")
_EVENT_TYPE_ENUM = _pg_enum(EventType, "event_type")


class Base(DeclarativeBase):
    pass


class PaymentORM(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(_CURRENCY_ENUM, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # `metadata` зарезервировано в DeclarativeBase -> атрибут и колонка названы `meta`.
    meta: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[PaymentStatus] = mapped_column(
        _PAYMENT_STATUS_ENUM,
        nullable=False,
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
    )
    webhook_url: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[Provider] = mapped_column(
        _PROVIDER_ENUM, nullable=False, server_default=Provider.MOCK.value
    )
    provider_ref: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        Index("ix_payments_status", "status"),
    )


class PaymentProviderIdempotencyStoreORM(Base):
    """Стор идемпотентности вызовов платёжного провайдера (в Postgres — общий для всех
    подов consumer'а). PaymentExecutor дедупит charge по ключу (payment.id): повторный
    вызов возвращает сохранённый результат, без нового списания."""

    __tablename__ = "payment_provider_idempotency_store"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OutboxORM(Base):
    __tablename__ = "payment_outbox"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[EventType] = mapped_column(_EVENT_TYPE_ENUM, nullable=False)
    routing_key: Mapped[str] = mapped_column(String(64), nullable=False)
    payment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        _OUTBOX_STATUS_ENUM, nullable=False, server_default=OutboxStatus.PENDING.value
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        # частичный индекс под опрос relay
        Index(
            "ix_payment_outbox_pending",
            "available_at",
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_payment_outbox_payment_id", "payment_id"),
    )
