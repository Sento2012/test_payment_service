from modules.Backend.Outbox.OutboxPaymentRepository.factory import (
    OutboxPaymentRepositoryServiceFactory,
)
from repository.entity.outbox_event import OutboxEvent
from modules.Backend.Outbox.OutboxPaymentRepository.Dto.outbox_event_transfer import (
    GetPendingEventsWithLockTransfer,
    OutboxEventDraftTransfer,
    OutboxEventUpdateTransfer,
)


class OutboxPaymentRepositoryServiceFacade:
    def __init__(self, outbox_payment_repository_service_factory: OutboxPaymentRepositoryServiceFactory) -> None:
        self._outbox_payment_repository_service_factory = outbox_payment_repository_service_factory

    async def create_outbox_event(
        self, outbox_event_draft_transfer: OutboxEventDraftTransfer
    ) -> OutboxEvent:
        return await self._outbox_payment_repository_service_factory.create_creator().create_outbox_event(
            outbox_event_draft_transfer
        )

    async def get_pending_events_with_lock(
        self, get_pending_events_with_lock_transfer: GetPendingEventsWithLockTransfer
    ) -> list[OutboxEvent]:
        return await self._outbox_payment_repository_service_factory.create_reader().get_pending_events_with_lock(
            get_pending_events_with_lock_transfer
        )

    async def update_outbox_event(
        self, outbox_event_update_transfer: OutboxEventUpdateTransfer
    ) -> None:
        await self._outbox_payment_repository_service_factory.create_updater().update_outbox_event(
            outbox_event_update_transfer
        )
