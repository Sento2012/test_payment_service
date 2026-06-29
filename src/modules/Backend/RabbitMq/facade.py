from modules.Backend.RabbitMq.RabbitMqManagement.facade import (
    RabbitMqManagementServiceFacade,
)
from shared.Dto.rabbitmq_transfer import PublishEventTransfer, PublishToQueueTransfer


class RabbitMqFacade:
    """Публичный API модуля RabbitMq. Только проксирует в RabbitMqManagement
    (собирается в DI)."""

    def __init__(
        self, rabbitmq_management_service_facade: RabbitMqManagementServiceFacade
    ) -> None:
        self._rabbitmq_management_service_facade = rabbitmq_management_service_facade

    async def publish_event(self, publish_event_transfer: PublishEventTransfer) -> None:
        await self._rabbitmq_management_service_facade.publish_event(
            publish_event_transfer
        )

    async def publish_to_queue(
        self, publish_to_queue_transfer: PublishToQueueTransfer
    ) -> None:
        await self._rabbitmq_management_service_facade.publish_to_queue(
            publish_to_queue_transfer
        )
