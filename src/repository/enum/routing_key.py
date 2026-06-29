from typing import Final


class RoutingKey:
    """Ключ маршрутизации события — часть персистентного состояния OutboxEvent
    (колонка routing_key в payment_outbox). Логический контракт producer↔transport,
    не зависит от конкретного брокера."""

    PAYMENTS_NEW: Final[str] = "payments.new"
