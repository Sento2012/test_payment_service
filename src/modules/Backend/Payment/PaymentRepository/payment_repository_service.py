from modules.Backend.Payment.PaymentRepository.dto import (
    PaymentCreateTransfer,
    PaymentFindTransfer,
    PaymentUpdateTransfer,
)
from repository.entity.payment import Payment
from repository.payment_repository_interface import PaymentRepositoryInterface
from shared.Port import UnitOfWork


class PaymentRepositoryService:
    """Доступ к платежам: чтение по фильтрам, создание из черновика, сохранение
    изменений (load → mutate → update). Работает в транзакции из контекста (enlisted)
    либо открывает свою короткую; принимает/возвращает бизнес-сущность Payment."""

    def __init__(
        self, unit_of_work: UnitOfWork, payment_repository: PaymentRepositoryInterface
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository = payment_repository

    async def find_payment(
        self, payment_find_transfer: PaymentFindTransfer
    ) -> Payment | None:
        async with self._unit_of_work.use_transaction(
            payment_find_transfer.context
        ) as session:
            return await self._payment_repository.find(
                session,
                payment_id=payment_find_transfer.payment_id,
                idempotency_key=payment_find_transfer.idempotency_key,
                for_update=payment_find_transfer.for_update,
            )

    async def create_payment(
        self, payment_create_transfer: PaymentCreateTransfer
    ) -> Payment:
        payment = Payment(
            idempotency_key=payment_create_transfer.idempotency_key,
            amount=payment_create_transfer.amount,
            currency=payment_create_transfer.currency,
            provider=payment_create_transfer.provider,
            webhook_url=payment_create_transfer.webhook_url,
            description=payment_create_transfer.description,
            meta=payment_create_transfer.meta,
        )
        async with self._unit_of_work.use_transaction(
            payment_create_transfer.context
        ) as session:
            return await self._payment_repository.create(session, payment)

    async def update_payment(
        self, payment_update_transfer: PaymentUpdateTransfer
    ) -> None:
        async with self._unit_of_work.use_transaction(
            payment_update_transfer.context
        ) as session:
            await self._payment_repository.update(
                session, payment_update_transfer.payment
            )
