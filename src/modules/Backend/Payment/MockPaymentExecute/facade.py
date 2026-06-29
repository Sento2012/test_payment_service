from modules.Backend.Payment.MockPaymentExecute.factory import (
    MockPaymentExecuteServiceFactory,
)
from modules.Backend.Payment.PaymentExecute.Dto.payment_execute_transfer import PaymentExecuteTransfer
from modules.Backend.Payment.PaymentExecute.Dto.provider_result_transfer import ProviderResultTransfer


class MockPaymentExecuteServiceFacade:
    """Публичный API сервиса MockPaymentExecute. Только проксирует в сервис."""

    def __init__(
        self, mock_payment_execute_service_factory: MockPaymentExecuteServiceFactory
    ) -> None:
        self._mock_payment_execute_service_factory = (
            mock_payment_execute_service_factory
        )

    async def execute_payment(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> ProviderResultTransfer:
        return await self._mock_payment_execute_service_factory.create_mock_payment_execute().execute_payment(
            payment_execute_transfer
        )
