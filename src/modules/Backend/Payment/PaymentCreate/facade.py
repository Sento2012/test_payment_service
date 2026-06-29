from repository.entity.payment import Payment
from modules.Backend.Payment.PaymentCreate.factory import (
    PaymentCreateServiceFactory,
)
from modules.Backend.Payment.PaymentCreate.Dto.payment_draft_transfer import (
    PaymentDraftTransfer,
)

class PaymentCreateServiceFacade:
    def __init__(self, payment_create_service_factory: PaymentCreateServiceFactory) -> None:
        self._payment_create_service_factory = payment_create_service_factory

    async def create_payment(
        self, payment_draft_transfer: PaymentDraftTransfer
    ) -> tuple[Payment, bool]:
        return await self._payment_create_service_factory.create_creator().create_payment(
            payment_draft_transfer
        )
