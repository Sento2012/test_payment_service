from repository.entity.payment import Payment
from repository.payment_repository import PaymentRepository
from modules.Backend.Payment.PaymentCreate.Dto.payment_draft_transfer import PaymentDraftTransfer
from shared.Port.persistence import UnitOfWork


class PaymentCreator:
    """Создание платежа. Строит сущность из черновика, открывает транзакцию из
    контекста (для атомарной записи с outbox) либо свою короткую."""

    def __init__(
        self, unit_of_work: UnitOfWork, payment_repository: PaymentRepository
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository = payment_repository

    async def create_payment(
        self, payment_draft_transfer: PaymentDraftTransfer
    ) -> Payment:
        payment = Payment(
            idempotency_key=payment_draft_transfer.idempotency_key,
            amount=payment_draft_transfer.amount,
            currency=payment_draft_transfer.currency,
            provider=payment_draft_transfer.provider,
            webhook_url=payment_draft_transfer.webhook_url,
            description=payment_draft_transfer.description,
            meta=payment_draft_transfer.meta,
        )
        async with self._unit_of_work.use_transaction(
            payment_draft_transfer.context
        ) as session:
            return await self._payment_repository.create(session, payment)
