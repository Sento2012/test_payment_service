from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.Persistence.orm import PaymentProviderIdempotencyStoreORM
from repository.entity.idempotency_record import IdempotencyRecord
from shared.Port import Transaction


class PaymentProviderIdempotencyStoreRepository:
    """Персистентность стора идемпотентности (SQLAlchemy). Stateless: сессия — параметр.

    Хэндл приходит как непрозрачный Transaction (порт) — конкретный AsyncSession
    известен только здесь, в адаптере, поэтому приводим его на входе."""

    async def find(
        self, transaction: Transaction, key: str
    ) -> IdempotencyRecord | None:
        session = cast(AsyncSession, transaction)
        orm = (
            await session.execute(
                select(PaymentProviderIdempotencyStoreORM).where(
                    PaymentProviderIdempotencyStoreORM.key == key
                )
            )
        ).scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def get_or_create(
        self, transaction: Transaction, idempotency_record: IdempotencyRecord
    ) -> IdempotencyRecord:
        """Записать, если ключа ещё нет (INSERT ON CONFLICT DO NOTHING), и вернуть
        ДЕЙСТВУЮЩУЮ запись — свою либо чужую (если кто-то записал раньше)."""
        session = cast(AsyncSession, transaction)
        await session.execute(
            insert(PaymentProviderIdempotencyStoreORM)
            .values(key=idempotency_record.key, value=idempotency_record.value)
            .on_conflict_do_nothing(index_elements=["key"])
        )
        await session.flush()
        orm = (
            await session.execute(
                select(PaymentProviderIdempotencyStoreORM).where(
                    PaymentProviderIdempotencyStoreORM.key == idempotency_record.key
                )
            )
        ).scalar_one()
        return self._to_entity(orm)

    def _to_entity(self, orm: PaymentProviderIdempotencyStoreORM) -> IdempotencyRecord:
        return IdempotencyRecord(
            key=orm.key, value=orm.value, created_at=orm.created_at
        )
