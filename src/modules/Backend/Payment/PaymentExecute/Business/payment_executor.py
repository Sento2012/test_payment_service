from modules.Backend.Idempotency.facade import IdempotencyFacade
from modules.Backend.Payment.PaymentExecute.Plugin.provider_execute_plugin_interface import (
    ProviderExecutePluginInterface,
)
from repository.enum.payment_status import PaymentStatus

from modules.Backend.Idempotency.PaymentProviderIdempotencyStoreRepository.Dto.idempotency_transfer import (
    IdempotencyKeyTransfer,
    IdempotencyRecordDraftTransfer,
)
from modules.Backend.Payment.PaymentExecute.Dto.payment_execute_transfer import PaymentExecuteTransfer
from modules.Backend.Payment.PaymentExecute.Dto.provider_result_transfer import ProviderResultTransfer

class UnknownProviderError(Exception):
    def __init__(self, provider: str) -> None:
        super().__init__(f"No provider plugin registered for '{provider}'")
        self.provider = provider

class PaymentExecutor:
    """Находит применимый плагин провайдера (is_applicable) и выполняет платёж.

    Идемпотентность charge — общая для всех провайдеров (здесь, а не в плагине): по
    ключу payment.id результат сохраняется через модуль Idempotency; повторный вызов с
    тем же ключом возвращает сохранённый результат БЕЗ нового списания (защита от
    двойного charge при краше между списанием и commit'ом, в т.ч. между подами)."""

    def __init__(
        self,
        provider_execute_plugins: list[ProviderExecutePluginInterface],
        idempotency_facade: IdempotencyFacade,
    ) -> None:
        self._provider_execute_plugins = provider_execute_plugins
        self._idempotency_facade = idempotency_facade

    def _resolve(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> ProviderExecutePluginInterface:
        for plugin in self._provider_execute_plugins:
            if plugin.is_applicable(payment_execute_transfer):
                return plugin
        raise UnknownProviderError(payment_execute_transfer.payment.provider.value)

    async def execute_payment(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> ProviderResultTransfer:
        idempotency_key = f"gateway:charge:{payment_execute_transfer.payment.id}"
        existing = await self._idempotency_facade.find_record(
            IdempotencyKeyTransfer(key=idempotency_key)
        )
        if existing is not None:
            return self._to_result(existing.value)

        result = await self._resolve(payment_execute_transfer).execute_payment(
            payment_execute_transfer
        )
        # сохраняем атомарно; вернётся действующее значение (если кто-то успел раньше)
        stored = await self._idempotency_facade.get_or_create_record(
            IdempotencyRecordDraftTransfer(
                key=idempotency_key, value=self._to_value(result)
            )
        )
        return self._to_result(stored.value)

    def _to_value(self, result: ProviderResultTransfer) -> dict:
        return {
            "status": result.status.value,
            "provider_ref": result.provider_ref,
            "failure_reason": result.failure_reason,
        }

    def _to_result(self, value: dict) -> ProviderResultTransfer:
        return ProviderResultTransfer(
            status=PaymentStatus(value["status"]),
            provider_ref=value.get("provider_ref"),
            failure_reason=value.get("failure_reason"),
        )
