from faststream.rabbit import RabbitBroker

from infrastructure.Messaging.topology import PAYMENTS_EXCHANGE
from shared.Dto import PublishEventTransfer, PublishToQueueTransfer
from shared.Port import MessagePublisher


class RabbitMqPublisher(MessagePublisher):
    """Реализация порта MessagePublisher поверх RabbitMQ/FastStream."""

    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish_event(self, publish_event_transfer: PublishEventTransfer) -> None:
        """Публикация доменного события в основной обменник (используется relay)."""
        await self._broker.publish(
            publish_event_transfer.payload,
            exchange=PAYMENTS_EXCHANGE,
            routing_key=publish_event_transfer.routing_key,
            message_id=publish_event_transfer.message_id,
            headers=publish_event_transfer.headers,
            persist=True,
        )

    async def publish_to_queue(
        self, publish_to_queue_transfer: PublishToQueueTransfer
    ) -> None:
        """Прямая публикация в очередь через default exchange (retry/DLQ)."""
        await self._broker.publish(
            publish_to_queue_transfer.payload,
            queue=publish_to_queue_transfer.queue_name,
            message_id=publish_to_queue_transfer.message_id,
            headers=publish_to_queue_transfer.headers,
            persist=True,
        )
