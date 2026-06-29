from typing import Final


class Exchange:
    """Обменники RabbitMQ."""

    PAYMENTS: Final[str] = "payments"
    PAYMENTS_DLX: Final[str] = "payments.dlx"
