from modules.Backend.Payment.MockPaymentExecute.mock_payment_execute import (
    MockPaymentExecute,
)
from modules.Backend.Payment.PaymentExecute import (
    PaymentExecuteTransfer,
    ProviderResultTransfer,
)
from modules.Backend.Payment.PaymentExecute.Plugin.provider_execute_plugin_interface import (
    ProviderExecutePluginInterface,
)
from repository.enum.provider import Provider


class MockProviderExecutePlugin(ProviderExecutePluginInterface):
    """Реализация контракта PaymentExecute для провайдера mock.

    Применимость — по payment.provider (типизированное сравнение enum'ов);
    исполнение делегирует в сервис MockPaymentExecute."""

    def __init__(self, mock_payment_execute: MockPaymentExecute) -> None:
        self._mock_payment_execute = mock_payment_execute

    def is_applicable(self, payment_execute_transfer: PaymentExecuteTransfer) -> bool:
        return payment_execute_transfer.payment.provider == Provider.MOCK

    async def execute_payment(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> ProviderResultTransfer:
        return await self._mock_payment_execute.execute_payment(
            payment_execute_transfer
        )
