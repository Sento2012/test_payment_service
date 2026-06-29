from abc import ABC, abstractmethod

from shared.Dto.rabbitmq_transfer import PublishEventTransfer, PublishToQueueTransfer


class MessagePublisher(ABC):
    """Порт публикации сообщений в брокер. Бизнес-слой зависит от абстракции;
    конкретная реализация (RabbitMQ/FastStream) — в infrastructure."""

    @abstractmethod
    async def publish_event(self, publish_event_transfer: PublishEventTransfer) -> None: ...

    @abstractmethod
    async def publish_to_queue(
        self, publish_to_queue_transfer: PublishToQueueTransfer
    ) -> None: ...
