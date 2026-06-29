from typing import Final


class Queue:
    """Очереди RabbitMQ."""

    PAYMENTS_NEW: Final[str] = "payments.new"
    PAYMENTS_NEW_DLQ: Final[str] = "payments.new.dlq"

    @staticmethod
    def retry(level: int) -> str:
        return f"payments.new.retry.{level}"
