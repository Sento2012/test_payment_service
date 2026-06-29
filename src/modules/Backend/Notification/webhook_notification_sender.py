import logging
from datetime import UTC, datetime

from modules.Backend.Notification.dto import WebhookNotificationTransfer
from modules.Backend.Payment.PaymentRepository import (
    PaymentFindTransfer,
    PaymentRepositoryService,
    PaymentUpdateTransfer,
)
from repository.entity.payment import Payment
from shared.Port import HttpClientInterface

logger = logging.getLogger(__name__)


class WebhookNotificationSender:
    """Доставка webhook-уведомления о результате платежа (load → guard → send → update).

    Идемпотентна по notified_at (повторная доставка сообщения webhook не дублирует).
    Ошибка доставки (сеть/не-2xx) поднимается выше — в consumer включается retry/DLQ.
    """

    def __init__(
        self,
        payment_repository_service: PaymentRepositoryService,
        http_client: HttpClientInterface,
    ) -> None:
        self._payment_repository_service = payment_repository_service
        self._http_client = http_client

    async def send_webhook_notification(
        self, webhook_notification_transfer: WebhookNotificationTransfer
    ) -> None:
        payment = await self._payment_repository_service.find_payment(
            PaymentFindTransfer(
                payment_id=webhook_notification_transfer.payment_id,
                context=webhook_notification_transfer.context,
            )
        )
        if payment is None:
            logger.warning(
                "send_webhook_notification: payment %s not found, skip",
                webhook_notification_transfer.payment_id,
            )
            return
        if payment.notified_at is not None:
            return  # уже доставлен (повторная доставка сообщения)
        if not payment.webhook_url:
            return  # отправлять некуда

        await self._http_client.post(payment.webhook_url, self._build_payload(payment))
        payment.notified_at = datetime.now(UTC)
        await self._payment_repository_service.update_payment(
            PaymentUpdateTransfer(payment=payment)
        )

    def _build_payload(self, payment: Payment) -> dict:
        return {
            "payment_id": str(payment.id),
            "status": payment.status.value,
            "amount": str(payment.amount),
            "currency": payment.currency.value,
            "description": payment.description,
            "provider": payment.provider.value,
            "provider_ref": payment.provider_ref,
            "failure_reason": payment.failure_reason,
            "meta": payment.meta,
        }
