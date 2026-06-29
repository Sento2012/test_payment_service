"""OutboxRelay.relay_pending_events — публикует pending-события в payments.new и
помечает их published в БД."""
from decimal import Decimal

from sqlalchemy import select

from infrastructure.Persistence.orm import OutboxORM
from modules.Backend.Payment.PaymentCreate.dto import PaymentDraftTransfer
from repository.enum.currency import Currency
from repository.enum.outbox_status import OutboxStatus


def _draft(idempotency_key: str) -> PaymentDraftTransfer:
    return PaymentDraftTransfer(
        idempotency_key=idempotency_key,
        amount=Decimal("10.00"),
        currency=Currency.RUB,
        webhook_url="https://wh.test/hook",
    )


async def test_relay_publishes_to_queue_and_marks_published(make_container, db, rabbit):
    container = make_container()
    payment, _ = await container.payment_creator().create_payment(_draft("relay-1"))

    processed = await container.outbox_relay().relay_pending_events()

    assert processed == 1
    message = await rabbit.get_message("payments.new")
    assert message is not None
    assert message["payment_id"] == str(payment.id)
    status = (
        await db.execute(
            select(OutboxORM.status).where(OutboxORM.payment_id == payment.id)
        )
    ).scalar_one()
    assert status == OutboxStatus.PUBLISHED


async def test_relay_no_pending_does_nothing(make_container, rabbit):
    container = make_container()

    processed = await container.outbox_relay().relay_pending_events()

    assert processed == 0
    assert await rabbit.get_message("payments.new") is None
