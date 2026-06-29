from dataclasses import dataclass

from repository.entity.payment import Payment


@dataclass(slots=True)
class PaymentExecuteTransfer:
    """Загруженный платёж для исполнения во внешнем шлюзе (вход PaymentExecute)."""

    payment: Payment
