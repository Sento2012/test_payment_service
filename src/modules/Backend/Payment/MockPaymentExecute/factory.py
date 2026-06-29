from config.groups import GatewaySettings
from modules.Backend.Payment.MockPaymentExecute.Business.mock_payment_execute import (
    MockPaymentExecute,
)


class MockPaymentExecuteServiceFactory:
    def __init__(self, gateway_settings: GatewaySettings) -> None:
        self._gateway_settings = gateway_settings

    def create_mock_payment_execute(self) -> MockPaymentExecute:
        return MockPaymentExecute(self._gateway_settings)
