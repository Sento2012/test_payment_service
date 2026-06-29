from dataclasses import dataclass, field


@dataclass(slots=True)
class PublishEventTransfer:
    """Публикация события в обменник (routing key)."""

    routing_key: str
    payload: dict
    message_id: str
    headers: dict = field(default_factory=dict)


@dataclass(slots=True)
class PublishToQueueTransfer:
    """Прямая публикация в очередь (default exchange)."""

    queue_name: str
    payload: dict
    message_id: str | None = None
    headers: dict = field(default_factory=dict)
