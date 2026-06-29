from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.Persistence.orm import OutboxORM
from repository.entity.outbox_event import OutboxEvent
from repository.enum.outbox_status import OutboxStatus


class OutboxRepository:
    """Персистентность payment_outbox (SQLAlchemy). Принимает/возвращает сущность
    OutboxEvent. Stateless: сессия передаётся в каждый метод."""

    def _to_entity(self, orm: OutboxORM) -> OutboxEvent:
        return OutboxEvent(
            id=orm.id,
            event_type=orm.event_type,
            routing_key=orm.routing_key,
            payment_id=orm.payment_id,
            payload=orm.payload,
            status=orm.status,
            attempts=orm.attempts,
            available_at=orm.available_at,
            created_at=orm.created_at,
            published_at=orm.published_at,
            last_error=orm.last_error,
        )

    async def create(
        self, session: AsyncSession, outbox_event: OutboxEvent
    ) -> OutboxEvent:
        orm = OutboxORM(
            id=uuid4(),
            event_type=outbox_event.event_type,
            routing_key=outbox_event.routing_key,
            payment_id=outbox_event.payment_id,
            payload=outbox_event.payload,
            status=OutboxStatus.PENDING,
            attempts=0,
        )
        session.add(orm)
        await session.flush()
        await session.refresh(orm)
        return self._to_entity(orm)

    async def get_pending_events_with_lock(
        self, session: AsyncSession, limit: int
    ) -> list[OutboxEvent]:
        """FOR UPDATE SKIP LOCKED — несколько relay-инстансов не возьмут одну строку."""
        stmt = (
            select(OutboxORM)
            .where(
                OutboxORM.status == OutboxStatus.PENDING,
                OutboxORM.available_at <= func.now(),
            )
            .order_by(OutboxORM.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = (await session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]

    async def update(self, session: AsyncSession, outbox_event: OutboxEvent) -> None:
        """Сохранить изменяемые поля сущности (load → mutate → update)."""
        await session.execute(
            update(OutboxORM)
            .where(OutboxORM.id == outbox_event.id)
            .values(
                status=outbox_event.status,
                attempts=outbox_event.attempts,
                available_at=outbox_event.available_at,
                published_at=outbox_event.published_at,
                last_error=(outbox_event.last_error[:2000] if outbox_event.last_error else None),
            )
        )
