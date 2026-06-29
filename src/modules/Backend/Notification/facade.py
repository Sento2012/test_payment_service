from modules.Backend.Notification.WebhookNotificationService.facade import (
    WebhookNotificationServiceFacade,
)
from modules.Backend.Payment.PaymentProcessing.Dto.payment_reference_transfer import PaymentReferenceTransfer


class NotificationFacade:
    """Публичный API модуля Notification. Только проксирует в сервисы (собираются в DI)."""

    def __init__(
        self,
        *,
        webhook_notification_service_facade: WebhookNotificationServiceFacade,
    ) -> None:
        self._webhook_notification_service_facade = (
            webhook_notification_service_facade
        )

    async def send_webhook_notification(
        self, payment_reference_transfer: PaymentReferenceTransfer
    ) -> None:
        await self._webhook_notification_service_facade.send_webhook_notification(
            payment_reference_transfer
        )
