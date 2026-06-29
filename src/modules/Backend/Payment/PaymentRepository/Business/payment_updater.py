from repository.payment_repository import PaymentRepository
from modules.Backend.Payment.PaymentRepository.Dto.payment_repository_transfer import PaymentUpdateTransfer
from shared.Port.persistence import UnitOfWork


class PaymentUpdater:
    """Сохранение изменённой сущности платежа (load → mutate → update). Работает в
    транзакции из контекста, либо открывает свою короткую."""

    def __init__(
        self, unit_of_work: UnitOfWork, payment_repository: PaymentRepository
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository = payment_repository

    async def update_payment(
        self, payment_update_transfer: PaymentUpdateTransfer
    ) -> None:
        async with self._unit_of_work.use_transaction(
            payment_update_transfer.context
        ) as session:
            await self._payment_repository.update(
                session, payment_update_transfer.payment
            )
