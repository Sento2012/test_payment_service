from modules.Backend.Outbox.OutboxPaymentRepository.dto import (
    GetPendingEventsWithLockTransfer,
    OutboxEventDraftTransfer,
    OutboxEventUpdateTransfer,
)
from repository.entity.outbox_event import OutboxEvent
from repository.outbox_repository import OutboxRepository
from shared.Port import UnitOfWork


class OutboxPaymentRepositoryService:
    """Доступ к payment_outbox: создание события из черновика, чтение pending с
    блокировкой (FOR UPDATE SKIP LOCKED), сохранение изменений. Работает в транзакции
    из контекста (enlisted — атомарно с платежом/на время публикации relay) либо
    открывает свою короткую."""

    def __init__(
        self, unit_of_work: UnitOfWork, outbox_repository: OutboxRepository
    ) -> None:
        self._unit_of_work = unit_of_work
        self._outbox_repository = outbox_repository

    async def create_outbox_event(
        self, outbox_event_draft_transfer: OutboxEventDraftTransfer
    ) -> OutboxEvent:
        outbox_event = OutboxEvent(
            event_type=outbox_event_draft_transfer.event_type,
            routing_key=outbox_event_draft_transfer.routing_key,
            payment_id=outbox_event_draft_transfer.payment_id,
            payload=outbox_event_draft_transfer.payload,
        )
        async with self._unit_of_work.use_transaction(
            outbox_event_draft_transfer.context
        ) as session:
            return await self._outbox_repository.create(session, outbox_event)

    async def get_pending_events_with_lock(
        self, get_pending_events_with_lock_transfer: GetPendingEventsWithLockTransfer
    ) -> list[OutboxEvent]:
        async with self._unit_of_work.use_transaction(
            get_pending_events_with_lock_transfer.context
        ) as session:
            return await self._outbox_repository.get_pending_events_with_lock(
                session, get_pending_events_with_lock_transfer.limit
            )

    async def update_outbox_event(
        self, outbox_event_update_transfer: OutboxEventUpdateTransfer
    ) -> None:
        async with self._unit_of_work.use_transaction(
            outbox_event_update_transfer.context
        ) as session:
            await self._outbox_repository.update(
                session, outbox_event_update_transfer.outbox_event
            )
