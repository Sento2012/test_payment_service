from enum import Enum


class EventType(str, Enum):
    """Типы доменных событий outbox (нативный PG enum)."""

    PAYMENT_NEW = "payments.new"
