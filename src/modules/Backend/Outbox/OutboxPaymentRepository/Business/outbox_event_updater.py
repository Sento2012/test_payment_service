from repository.outbox_repository import OutboxRepository
from modules.Backend.Outbox.OutboxPaymentRepository.Dto.outbox_event_transfer import OutboxEventUpdateTransfer
from shared.Port.persistence import UnitOfWork


class OutboxEventUpdater:
    """Сохранение изменённой сущности события (load → mutate → update). Работает в
    транзакции из контекста, либо открывает свою короткую."""

    def __init__(
        self, unit_of_work: UnitOfWork, outbox_repository: OutboxRepository
    ) -> None:
        self._unit_of_work = unit_of_work
        self._outbox_repository = outbox_repository

    async def update_outbox_event(
        self, outbox_event_update_transfer: OutboxEventUpdateTransfer
    ) -> None:
        async with self._unit_of_work.use_transaction(
            outbox_event_update_transfer.context
        ) as session:
            await self._outbox_repository.update(
                session, outbox_event_update_transfer.outbox_event
            )
