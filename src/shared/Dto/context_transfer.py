from dataclasses import dataclass

from shared.Port.persistence import Transaction


@dataclass(slots=True)
class ContextTransfer:
    """Контекст вызова, который ходит вместе с DTO между сервисами.

    Несёт необязательную транзакцию: если она задана (например, PaymentCreate
    открыл её для атомарной записи), репозитории работают в ней; если нет —
    открывают собственную короткую транзакцию (через UnitOfWork.use_transaction).
    """

    transaction: Transaction | None = None
