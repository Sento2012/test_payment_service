from modules.Backend.Idempotency.facade import IdempotencyFacade
from modules.Backend.Payment.PaymentExecute.Business.payment_executor import (
    PaymentExecutor,
)
from modules.Backend.Payment.PaymentExecute.Plugin.provider_execute_plugin_interface import (
    ProviderExecutePluginInterface,
)


class PaymentExecuteServiceFactory:
    """Держит реестр плагинов-провайдеров (provider plugin stack) и фасад идемпотентности."""

    def __init__(
        self,
        provider_execute_plugins: list[ProviderExecutePluginInterface],
        idempotency_facade: IdempotencyFacade,
    ) -> None:
        self._provider_execute_plugins = provider_execute_plugins
        self._idempotency_facade = idempotency_facade

    def create_executor(self) -> PaymentExecutor:
        return PaymentExecutor(self._provider_execute_plugins, self._idempotency_facade)
