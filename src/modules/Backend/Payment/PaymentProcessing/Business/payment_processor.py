import logging
from datetime import datetime, timezone

from modules.Backend.Notification.facade import NotificationFacade
from modules.Backend.Payment.PaymentExecute.facade import PaymentExecuteServiceFacade
from modules.Backend.Payment.PaymentRepository.facade import (
    PaymentRepositoryServiceFacade,
)
from repository.entity.payment import Payment
from repository.enum.payment_status import PaymentStatus
from shared.Dto.context_transfer import ContextTransfer
from modules.Backend.Payment.PaymentExecute.Dto.payment_execute_transfer import (
    PaymentExecuteTransfer,
)
from modules.Backend.Payment.PaymentProcessing.Dto.payment_reference_transfer import (
    PaymentReferenceTransfer,
)
from modules.Backend.Payment.PaymentRepository.Dto.payment_repository_transfer import (
    PaymentConditionsTransfer,
    PaymentUpdateTransfer,
)
from shared.Port.persistence import UnitOfWork

logger = logging.getLogger(__name__)


class PaymentProcessor:
    """Обработка платежа на стороне consumer'а (load → mutate → update + нотификация).

    Защита от двойного списания при конкурентных дублях (relay at-least-once + prefetch>1):
    платёж читается с FOR UPDATE внутри транзакции, лок держится через вызов шлюза до
    commit'а статуса. Дубль того же платежа блокируется, после commit'а видит не-pending
    и пропускает обработку. Краш → rollback → лок снят, строка остаётся pending → повтор.
    Webhook — ВНЕ лока (модуль Notification, идемпотентен по notified_at).
    """

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        payment_repository_service_facade: PaymentRepositoryServiceFacade,
        payment_execute_service_facade: PaymentExecuteServiceFacade,
        notification_facade: NotificationFacade,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository_service_facade = payment_repository_service_facade
        self._payment_execute_service_facade = payment_execute_service_facade
        self._notification_facade = notification_facade

    async def process_payment(
        self, payment_reference_transfer: PaymentReferenceTransfer
    ) -> Payment | None:
        async with self._unit_of_work.begin() as transaction:
            context_transfer = ContextTransfer(transaction=transaction)
            # FOR UPDATE: захватываем платёж; конкурентный дубль ждёт на этом локе
            payment = await self._payment_repository_service_facade.find_payment(
                PaymentConditionsTransfer(
                    payment_id=payment_reference_transfer.payment_id,
                    for_update=True,
                    context=context_transfer,
                )
            )
            if payment is None:
                logger.warning(
                    "process_payment: payment %s not found, skip",
                    payment_reference_transfer.payment_id,
                )
                return None

            if payment.status == PaymentStatus.PENDING:
                logger.info(
                    "process_payment: executing payment %s via gateway", payment.id
                )
                provider_result_transfer = (
                    await self._payment_execute_service_facade.execute_payment(
                        PaymentExecuteTransfer(payment=payment)
                    )
                )
                payment.status = provider_result_transfer.status
                payment.provider_ref = provider_result_transfer.provider_ref
                payment.failure_reason = provider_result_transfer.failure_reason
                payment.processed_at = datetime.now(timezone.utc)
                await self._payment_repository_service_facade.update_payment(
                    PaymentUpdateTransfer(payment=payment, context=context_transfer)
                )
            # выход из блока → commit → лок снят (до сетевого вызова webhook)

        # по ТЗ уведомляем клиента о РЕЗУЛЬТАТЕ — и succeeded, и failed (бизнес-исход,
        # не ошибка обработки). Идемпотентно по notified_at — безопасно при повторной
        # доставке сообщения, даже если платёж уже был обработан ранее
        await self._notification_facade.send_webhook_notification(
            payment_reference_transfer
        )
        return payment
