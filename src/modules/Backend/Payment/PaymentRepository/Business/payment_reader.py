from repository.entity.payment import Payment
from repository.payment_repository import PaymentRepository
from modules.Backend.Payment.PaymentRepository.Dto.payment_repository_transfer import PaymentConditionsTransfer
from shared.Port.persistence import UnitOfWork


class PaymentReader:
    """Чтение платежей по фильтрам (общий метод). Открывает транзакцию из контекста
    либо свою короткую и отдаёт сессию репозиторию; возвращает бизнес-сущность."""

    def __init__(
        self, unit_of_work: UnitOfWork, payment_repository: PaymentRepository
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository = payment_repository

    async def find_payment(
        self, payment_conditions_transfer: PaymentConditionsTransfer
    ) -> Payment | None:
        async with self._unit_of_work.use_transaction(
            payment_conditions_transfer.context
        ) as session:
            return await self._payment_repository.find(
                session,
                payment_id=payment_conditions_transfer.payment_id,
                idempotency_key=payment_conditions_transfer.idempotency_key,
                for_update=payment_conditions_transfer.for_update,
            )
