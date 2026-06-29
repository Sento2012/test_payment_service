"""PaymentCreate.create_payment — атомарная запись payment + outbox, идемпотентность."""
from decimal import Decimal

from sqlalchemy import func, select

from infrastructure.Persistence.orm import OutboxORM, PaymentORM
from repository.enum.currency import Currency
from repository.enum.outbox_status import OutboxStatus
from repository.enum.payment_status import PaymentStatus
from modules.Backend.Payment.PaymentCreate.Dto.payment_draft_transfer import PaymentDraftTransfer


def _draft(idempotency_key: str = "create-1") -> PaymentDraftTransfer:
    return PaymentDraftTransfer(
        idempotency_key=idempotency_key,
        amount=Decimal("100.00"),
        currency=Currency.USD,
        webhook_url="https://wh.test/hook",
        description="t",
        meta={"user_id": 1},
    )


async def test_create_payment_persists_payment_and_outbox(make_container, db):
    container = make_container()

    payment, created = await container.payment_facade().create_payment(_draft())

    assert created is True
    status = (
        await db.execute(
            select(PaymentORM.status).where(PaymentORM.id == payment.id)
        )
    ).scalar_one()
    assert status == PaymentStatus.PENDING
    outbox = (
        await db.execute(
            select(OutboxORM.payment_id, OutboxORM.status, OutboxORM.routing_key).where(
                OutboxORM.payment_id == payment.id
            )
        )
    ).one()
    assert outbox.status == OutboxStatus.PENDING
    assert outbox.routing_key == "payments.new"


async def test_create_payment_is_idempotent_by_key(make_container, db):
    container = make_container()

    first, created_first = await container.payment_facade().create_payment(
        _draft("dup-key")
    )
    second, created_second = await container.payment_facade().create_payment(
        _draft("dup-key")
    )

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    payments = (
        await db.execute(select(func.count()).select_from(PaymentORM))
    ).scalar_one()
    outbox = (
        await db.execute(select(func.count()).select_from(OutboxORM))
    ).scalar_one()
    assert payments == 1
    assert outbox == 1
