from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.Persistence.orm import PaymentORM
from repository.entity.payment import Payment
from repository.enum.payment_status import PaymentStatus
from shared.Port import Transaction


class PaymentRepository:
    """Персистентность платежей (SQLAlchemy). Принимает/возвращает сущность Payment,
    маппит её на ORM. Stateless: сессия передаётся в каждый метод.

    Хэндл транзакции приходит как непрозрачный Transaction (порт) — конкретный тип
    AsyncSession известен только здесь, в адаптере, поэтому приводим его на входе."""

    async def create(self, transaction: Transaction, payment: Payment) -> Payment:
        session = cast(AsyncSession, transaction)
        orm = PaymentORM(
            id=payment.id,
            idempotency_key=payment.idempotency_key,
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            meta=payment.meta,
            status=payment.status or PaymentStatus.PENDING,
            webhook_url=payment.webhook_url,
            provider=payment.provider,
        )
        session.add(orm)
        await session.flush()
        await session.refresh(orm)
        return self._to_entity(orm)

    async def find(
        self,
        transaction: Transaction,
        payment_id: UUID | None = None,
        idempotency_key: str | None = None,
        for_update: bool = False,
    ) -> Payment | None:
        session = cast(AsyncSession, transaction)
        stmt = select(PaymentORM)
        if payment_id is not None:
            stmt = stmt.where(PaymentORM.id == payment_id)
        if idempotency_key is not None:
            stmt = stmt.where(PaymentORM.idempotency_key == idempotency_key)
        if for_update:
            stmt = stmt.with_for_update()  # row-lock до конца транзакции
        orm = (await session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def update(self, transaction: Transaction, payment: Payment) -> None:
        """Сохранить изменяемые поля сущности (load → mutate → update)."""
        session = cast(AsyncSession, transaction)
        await session.execute(
            update(PaymentORM)
            .where(PaymentORM.id == payment.id)
            .values(
                status=payment.status,
                provider_ref=payment.provider_ref,
                failure_reason=payment.failure_reason,
                processed_at=payment.processed_at,
                notified_at=payment.notified_at,
            )
        )

    def _to_entity(self, orm: PaymentORM) -> Payment:
        return Payment(
            id=orm.id,
            idempotency_key=orm.idempotency_key,
            amount=orm.amount,
            currency=orm.currency,
            status=orm.status,
            provider=orm.provider,
            webhook_url=orm.webhook_url,
            description=orm.description,
            meta=orm.meta,
            provider_ref=orm.provider_ref,
            failure_reason=orm.failure_reason,
            created_at=orm.created_at,
            processed_at=orm.processed_at,
            notified_at=orm.notified_at,
        )
