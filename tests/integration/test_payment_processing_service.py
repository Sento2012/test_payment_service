"""PaymentProcessing.process_payment — обработка через шлюз, статус в БД, webhook,
идемпотентность (стор + повторная обработка)."""
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from conftest import FakeHttpClient
from infrastructure.Persistence.orm import (
    PaymentORM,
    PaymentProviderIdempotencyStoreORM,
)
from modules.Backend.Payment.PaymentCreate.dto import PaymentDraftTransfer
from modules.Backend.Payment.PaymentProcessing.dto import PaymentReferenceTransfer
from repository.enum.currency import Currency
from repository.enum.payment_status import PaymentStatus


def _draft(idempotency_key: str) -> PaymentDraftTransfer:
    return PaymentDraftTransfer(
        idempotency_key=idempotency_key,
        amount=Decimal("50.00"),
        currency=Currency.EUR,
        webhook_url="https://wh.test/hook",
    )


async def _create_pending(container, key: str):
    payment, _ = await container.payment_creator().create_payment(_draft(key))
    return payment


async def test_process_payment_success_updates_db_and_sends_webhook(make_container, db):
    fake_http = FakeHttpClient()
    container = make_container(success_rate=1.0, http_client=fake_http)
    payment = await _create_pending(container, "proc-ok")

    await container.payment_processor().process_payment(
        PaymentReferenceTransfer(payment_id=payment.id)
    )

    row = (
        await db.execute(
            select(
                PaymentORM.status,
                PaymentORM.provider_ref,
                PaymentORM.processed_at,
                PaymentORM.notified_at,
            ).where(PaymentORM.id == payment.id)
        )
    ).one()
    assert row.status == PaymentStatus.SUCCEEDED
    assert row.provider_ref is not None
    assert row.processed_at is not None
    assert row.notified_at is not None
    assert len(fake_http.calls) == 1
    store = (
        await db.execute(
            select(func.count()).select_from(PaymentProviderIdempotencyStoreORM)
        )
    ).scalar_one()
    assert store == 1


async def test_process_payment_failure_still_sends_webhook(make_container, db):
    fake_http = FakeHttpClient()
    container = make_container(success_rate=0.0, http_client=fake_http)
    payment = await _create_pending(container, "proc-fail")

    await container.payment_processor().process_payment(
        PaymentReferenceTransfer(payment_id=payment.id)
    )

    row = (
        await db.execute(
            select(
                PaymentORM.status,
                PaymentORM.failure_reason,
                PaymentORM.notified_at,
            ).where(PaymentORM.id == payment.id)
        )
    ).one()
    assert row.status == PaymentStatus.FAILED
    assert row.failure_reason is not None
    assert row.notified_at is not None  # о результате уведомляем и при failed
    assert len(fake_http.calls) == 1


async def test_process_payment_webhook_error_propagates(make_container, db):
    fake_http = FakeHttpClient(fail=True)
    container = make_container(success_rate=1.0, http_client=fake_http)
    payment = await _create_pending(container, "proc-wh-fail")

    with pytest.raises(RuntimeError):
        await container.payment_processor().process_payment(
            PaymentReferenceTransfer(payment_id=payment.id)
        )

    # платёж обработан (provider отработал), но webhook не доставлен -> consumer уйдёт в retry
    row = (
        await db.execute(
            select(PaymentORM.status, PaymentORM.notified_at).where(
                PaymentORM.id == payment.id
            )
        )
    ).one()
    assert row.status == PaymentStatus.SUCCEEDED
    assert row.notified_at is None


async def test_process_payment_reprocessing_is_idempotent(make_container, db):
    fake_http = FakeHttpClient()
    container = make_container(success_rate=1.0, http_client=fake_http)
    payment = await _create_pending(container, "proc-twice")
    reference = PaymentReferenceTransfer(payment_id=payment.id)

    await container.payment_processor().process_payment(reference)
    first_ref = (
        await db.execute(
            select(PaymentORM.provider_ref).where(PaymentORM.id == payment.id)
        )
    ).scalar_one()

    await container.payment_processor().process_payment(reference)  # повторная доставка
    second_ref = (
        await db.execute(
            select(PaymentORM.provider_ref).where(PaymentORM.id == payment.id)
        )
    ).scalar_one()

    assert first_ref == second_ref  # шлюз не дёргался повторно
    assert len(fake_http.calls) == 1  # webhook не отправлен повторно (guard notified_at)
    store = (
        await db.execute(
            select(func.count()).select_from(PaymentProviderIdempotencyStoreORM)
        )
    ).scalar_one()
    assert store == 1


async def test_process_payment_unknown_id_returns_none(make_container):
    container = make_container()

    result = await container.payment_processor().process_payment(
        PaymentReferenceTransfer(payment_id=uuid4())
    )

    assert result is None
