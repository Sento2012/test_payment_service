from infrastructure.Http.http_client_interface import HttpClientInterface
from modules.Backend.Notification.WebhookNotificationService.Business.webhook_notification_sender import (
    WebhookNotificationSender,
)
from modules.Backend.Payment.PaymentRepository.facade import (
    PaymentRepositoryServiceFacade,
)


class WebhookNotificationServiceFactory:
    def __init__(
        self,
        payment_repository_service_facade: PaymentRepositoryServiceFacade,
        http_client: HttpClientInterface,
    ) -> None:
        self._payment_repository_service_facade = payment_repository_service_facade
        self._http_client = http_client

    def create_sender(self) -> WebhookNotificationSender:
        return WebhookNotificationSender(
            self._payment_repository_service_facade, self._http_client
        )
