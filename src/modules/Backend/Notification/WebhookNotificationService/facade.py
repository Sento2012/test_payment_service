from modules.Backend.Notification.WebhookNotificationService.factory import (
    WebhookNotificationServiceFactory,
)
from modules.Backend.Payment.PaymentProcessing.Dto.payment_reference_transfer import PaymentReferenceTransfer


class WebhookNotificationServiceFacade:
    """Публичный API сервиса WebhookNotificationService. Только проксирует."""

    def __init__(
        self, webhook_notification_service_factory: WebhookNotificationServiceFactory
    ) -> None:
        self._webhook_notification_service_factory = (
            webhook_notification_service_factory
        )

    async def send_webhook_notification(
        self, payment_reference_transfer: PaymentReferenceTransfer
    ) -> None:
        await self._webhook_notification_service_factory.create_sender().send_webhook_notification(
            payment_reference_transfer
        )
