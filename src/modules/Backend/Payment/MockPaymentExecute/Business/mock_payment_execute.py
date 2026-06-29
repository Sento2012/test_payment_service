import asyncio
import random
from uuid import uuid4

from config.groups import GatewaySettings
from repository.enum.payment_status import PaymentStatus
from modules.Backend.Payment.PaymentExecute.Dto.payment_execute_transfer import PaymentExecuteTransfer
from modules.Backend.Payment.PaymentExecute.Dto.provider_result_transfer import ProviderResultTransfer


class MockPaymentExecute:
    """Эмуляция платёжного шлюза: задержка 2–5с, 90% success / 10% failed.

    Только сам «charge» — дедупликация по idempotency-ключу вынесена в PaymentExecutor
    (общая для всех провайдеров)."""

    def __init__(self, gateway_settings: GatewaySettings) -> None:
        self._gateway_settings = gateway_settings

    async def execute_payment(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> ProviderResultTransfer:
        delay = random.uniform(
            self._gateway_settings.min_delay, self._gateway_settings.max_delay
        )
        await asyncio.sleep(delay)

        if random.random() < self._gateway_settings.success_rate:
            return ProviderResultTransfer(
                status=PaymentStatus.SUCCEEDED,
                provider_ref=f"mock_{uuid4().hex}",
            )
        return ProviderResultTransfer(
            status=PaymentStatus.FAILED,
            failure_reason="Payment declined by provider (emulated)",
        )
