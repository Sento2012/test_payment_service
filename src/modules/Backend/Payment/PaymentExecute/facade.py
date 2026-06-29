from modules.Backend.Payment.PaymentExecute.factory import (
    PaymentExecuteServiceFactory,
)

from modules.Backend.Payment.PaymentExecute.Dto.payment_execute_transfer import PaymentExecuteTransfer
from modules.Backend.Payment.PaymentExecute.Dto.provider_result_transfer import ProviderResultTransfer

class PaymentExecuteServiceFacade:
    def __init__(self, payment_execute_service_factory: PaymentExecuteServiceFactory) -> None:
        self._payment_execute_service_factory = payment_execute_service_factory

    async def execute_payment(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> ProviderResultTransfer:
        return await self._payment_execute_service_factory.create_executor().execute_payment(payment_execute_transfer)
