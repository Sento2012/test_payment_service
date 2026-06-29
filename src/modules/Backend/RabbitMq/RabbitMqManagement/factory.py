from shared.Port.messaging import MessagePublisher


class RabbitMqManagementServiceFactory:
    """Держит инжектированный publisher (порт). Конкретная реализация — в infra."""

    def __init__(self, message_publisher: MessagePublisher) -> None:
        self._message_publisher = message_publisher

    def create_publisher(self) -> MessagePublisher:
        return self._message_publisher
