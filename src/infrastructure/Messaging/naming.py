"""Имена топологии RabbitMQ (обменники, очереди) и служебные заголовки сообщений.

Чистая инфраструктура — как разведён брокер. Домен этого не знает; persisted-контракт
маршрутизации (RoutingKey) живёт в repository/enum."""
from typing import Final


class Exchange:
    """Обменники RabbitMQ."""

    PAYMENTS: Final[str] = "payments"
    PAYMENTS_DLX: Final[str] = "payments.dlx"


class Queue:
    """Очереди RabbitMQ."""

    PAYMENTS_NEW: Final[str] = "payments.new"
    PAYMENTS_NEW_DLQ: Final[str] = "payments.new.dlq"

    @staticmethod
    def retry(level: int) -> str:
        return f"payments.new.retry.{level}"


class MessageHeader:
    """Служебные заголовки сообщений."""

    ATTEMPT: Final[str] = "x-attempt"  # счётчик попыток обработки (наш, не x-death)
