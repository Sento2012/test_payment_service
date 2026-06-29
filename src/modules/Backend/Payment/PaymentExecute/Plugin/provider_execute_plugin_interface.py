from abc import ABC, abstractmethod

from modules.Backend.Payment.PaymentExecute.dto import (
    PaymentExecuteTransfer,
    ProviderResultTransfer,
)


class ProviderExecutePluginInterface(ABC):
    """Контракт плагина платёжного провайдера (объявлен модулем PaymentExecute).

    Новый провайдер = отдельный сервис в модуле Payment, реализующий этот контракт
    плагином в своей папке Plugin/. Применимость плагин решает сам в is_applicable."""

    @abstractmethod
    def is_applicable(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> bool:
        """Подходит ли плагин для этого платежа (обычно по payment.provider)."""
        ...

    @abstractmethod
    async def execute_payment(
        self, payment_execute_transfer: PaymentExecuteTransfer
    ) -> ProviderResultTransfer:
        """Выполнить платёж во внешнем шлюзе. Возвращает бизнес-результат
        (succeeded/failed), а не бросает исключение на отказ оплаты."""
        ...
