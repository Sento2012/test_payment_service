from modules.Backend.RabbitMq.RabbitMqManagement.factory import (
    RabbitMqManagementServiceFactory,
)
from shared.Dto.rabbitmq_transfer import PublishEventTransfer, PublishToQueueTransfer


class RabbitMqManagementServiceFacade:
    """Публичный API сервиса. Делегирует в бизнес-логику через фабрику."""

    def __init__(self, rabbitmq_management_service_factory: RabbitMqManagementServiceFactory) -> None:
        self._rabbitmq_management_service_factory = rabbitmq_management_service_factory

    async def publish_event(self, publish_event_transfer: PublishEventTransfer) -> None:
        await self._rabbitmq_management_service_factory.create_publisher().publish_event(publish_event_transfer)

    async def publish_to_queue(
        self, publish_to_queue_transfer: PublishToQueueTransfer
    ) -> None:
        await self._rabbitmq_management_service_factory.create_publisher().publish_to_queue(
            publish_to_queue_transfer
        )
