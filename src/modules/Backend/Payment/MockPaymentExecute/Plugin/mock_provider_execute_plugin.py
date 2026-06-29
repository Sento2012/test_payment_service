from modules.Backend.Payment.MockPaymentExecute.facade import (
    MockPaymentExecuteServiceFacade,
)
from modules.Backend.Payment.PaymentExecute.Plugin.provider_execute_plugin_interface import (
    ProviderExecutePluginInterface,
)
from repository.enum.provider import Provider
from modules.Backend.Payment.PaymentExecute.Dto.payment_execute_transfer import PaymentExecuteTransfer
from modules.Backend.Payment.PaymentExecute.Dto.provider_result_transfer import ProviderResultTransfer


class MockProviderExecutePlugin(ProviderExecutePluginInterface):
    """Реализация контракта PaymentExecute для провайдера mock.

    Применимость — по payment.provider (типизированное сравнение enum'ов);
    исполнение делегирует в фасад сервиса MockPaymentExecute."""

    def __init__(
        self, mock_payment_execute_service_facade: MockPaymentExecuteServiceFacade
    ) -> None:
        self._mock_payment_execute_service_facade = (
            mock_payment_execute_service_facade
        )

    def is_applicable(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> bool:
        return payment_execute_transfer.payment.provider == Provider.MOCK

    async def execute_payment(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> ProviderResultTransfer:
        return await self._mock_payment_execute_service_facade.execute_payment(
            payment_execute_transfer
        )
