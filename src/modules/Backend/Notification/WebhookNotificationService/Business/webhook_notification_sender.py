import logging
from datetime import datetime, timezone

from infrastructure.Http.http_client_interface import HttpClientInterface
from modules.Backend.Payment.PaymentRepository.facade import (
    PaymentRepositoryServiceFacade,
)
from repository.entity.payment import Payment
from modules.Backend.Payment.PaymentProcessing.Dto.payment_reference_transfer import (
    PaymentReferenceTransfer,
)
from modules.Backend.Payment.PaymentRepository.Dto.payment_repository_transfer import (
    PaymentConditionsTransfer,
    PaymentUpdateTransfer,
)

logger = logging.getLogger(__name__)


class WebhookNotificationSender:
    """Доставка webhook-уведомления о результате платежа (load → guard → send → update).

    Идемпотентна по notified_at (повторная доставка сообщения webhook не дублирует).
    Ошибка доставки (сеть/не-2xx) поднимается выше — в consumer включается retry/DLQ.
    """

    def __init__(
        self,
        payment_repository_service_facade: PaymentRepositoryServiceFacade,
        http_client: HttpClientInterface,
    ) -> None:
        self._payment_repository_service_facade = payment_repository_service_facade
        self._http_client = http_client

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

    async def send_webhook_notification(
        self, payment_reference_transfer: PaymentReferenceTransfer
    ) -> None:
        payment = await self._payment_repository_service_facade.find_payment(
            PaymentConditionsTransfer(
                payment_id=payment_reference_transfer.payment_id,
                context=payment_reference_transfer.context,
            )
        )
        if payment is None:
            logger.warning(
                "send_webhook_notification: payment %s not found, skip",
                payment_reference_transfer.payment_id,
            )
            return
        if payment.notified_at is not None:
            return  # уже доставлен (повторная доставка сообщения)
        if not payment.webhook_url:
            return  # отправлять некуда

        await self._http_client.post(payment.webhook_url, self._build_payload(payment))
        payment.notified_at = datetime.now(timezone.utc)
        await self._payment_repository_service_facade.update_payment(
            PaymentUpdateTransfer(payment=payment)
        )
