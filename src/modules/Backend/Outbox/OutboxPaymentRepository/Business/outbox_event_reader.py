from repository.entity.outbox_event import OutboxEvent
from repository.outbox_repository import OutboxRepository
from modules.Backend.Outbox.OutboxPaymentRepository.Dto.outbox_event_transfer import GetPendingEventsWithLockTransfer
from shared.Port.persistence import UnitOfWork


class OutboxEventReader:
    """Чтение pending-событий с блокировкой (FOR UPDATE SKIP LOCKED). Работает в
    транзакции из контекста (её держит relay на время публикации) либо открывает свою."""

    def __init__(
        self, unit_of_work: UnitOfWork, outbox_repository: OutboxRepository
    ) -> None:
        self._unit_of_work = unit_of_work
        self._outbox_repository = outbox_repository

    async def get_pending_events_with_lock(
        self, get_pending_events_with_lock_transfer: GetPendingEventsWithLockTransfer
    ) -> list[OutboxEvent]:
        async with self._unit_of_work.use_transaction(
            get_pending_events_with_lock_transfer.context
        ) as session:
            return await self._outbox_repository.get_pending_events_with_lock(
                session, get_pending_events_with_lock_transfer.limit
            )
