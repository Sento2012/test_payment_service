from modules.Backend.Outbox.OutboxPaymentRepository.facade import (
    OutboxPaymentRepositoryServiceFacade,
)
from modules.Backend.Outbox.OutboxRelay.facade import OutboxRelayServiceFacade
from repository.entity.outbox_event import OutboxEvent
from modules.Backend.Outbox.OutboxPaymentRepository.Dto.outbox_event_transfer import OutboxEventDraftTransfer


class OutboxFacade:
    """Публичный API модуля Outbox. Только проксирует в сервисы (собираются в DI)."""

    def __init__(
        self,
        *,
        outbox_payment_repository_service_facade: OutboxPaymentRepositoryServiceFacade,
        outbox_relay_service_facade: OutboxRelayServiceFacade,
    ) -> None:
        self._outbox_payment_repository_service_facade = (
            outbox_payment_repository_service_facade
        )
        self._outbox_relay_service_facade = outbox_relay_service_facade

    async def create_outbox_event(
        self, outbox_event_draft_transfer: OutboxEventDraftTransfer
    ) -> OutboxEvent:
        return await self._outbox_payment_repository_service_facade.create_outbox_event(
            outbox_event_draft_transfer
        )

    async def relay_pending_events(self) -> int:
        return await self._outbox_relay_service_facade.relay_pending_events()
