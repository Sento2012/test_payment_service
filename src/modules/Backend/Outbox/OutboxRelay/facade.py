from modules.Backend.Outbox.OutboxRelay.factory import (
    OutboxRelayServiceFactory,
)


class OutboxRelayServiceFacade:
    def __init__(self, outbox_relay_service_factory: OutboxRelayServiceFactory) -> None:
        self._outbox_relay_service_factory = outbox_relay_service_factory

    async def relay_pending_events(self) -> int:
        return await self._outbox_relay_service_factory.create_relay().relay_pending_events()
