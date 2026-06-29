from faststream.rabbit import RabbitBroker

from config.settings import get_settings

_broker: RabbitBroker | None = None


def get_broker() -> RabbitBroker:
    """Единый (на процесс) низкоуровневый брокер RabbitMQ.

    Инфраструктурный примитив: создание/конфигурация подключения. Бизнес-слой сюда
    не обращается — он работает через RabbitMqFacade. Подключение
    (connect/start) — ответственность приложения (consumer/relay) на старте.
    """
    global _broker
    if _broker is None:
        settings = get_settings()
        # max_consumers = QoS prefetch (актуально для consumer-процесса).
        _broker = RabbitBroker(
            settings.rabbitmq_url, max_consumers=settings.consumer.prefetch
        )
    return _broker
