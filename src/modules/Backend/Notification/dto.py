from dataclasses import dataclass, field
from uuid import UUID

from shared.Dto import ContextTransfer


@dataclass(slots=True)
class WebhookNotificationTransfer:
    """Ссылка на платёж для доставки webhook-уведомления — вход
    send_webhook_notification. Собственный DTO Notification (не зависит от чужих)."""

    payment_id: UUID
    context: ContextTransfer = field(default_factory=ContextTransfer)
