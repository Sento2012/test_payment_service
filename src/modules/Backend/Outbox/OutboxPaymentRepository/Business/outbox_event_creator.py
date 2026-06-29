from repository.entity.outbox_event import OutboxEvent
from repository.outbox_repository import OutboxRepository
from modules.Backend.Outbox.OutboxPaymentRepository.Dto.outbox_event_transfer import OutboxEventDraftTransfer
from shared.Port.persistence import UnitOfWork


class OutboxEventCreator:
    """Создание события outbox. Строит сущность из черновика, работает в транзакции
    из контекста (для атомарной записи с платежом) либо открывает свою короткую."""

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
