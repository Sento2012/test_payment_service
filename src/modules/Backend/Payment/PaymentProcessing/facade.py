from repository.entity.payment import Payment
from modules.Backend.Payment.PaymentProcessing.factory import (
    PaymentProcessingServiceFactory,
)
from modules.Backend.Payment.PaymentProcessing.Dto.payment_reference_transfer import PaymentReferenceTransfer

class PaymentProcessingServiceFacade:
    def __init__(self, payment_processing_service_factory: PaymentProcessingServiceFactory) -> None:
        self._payment_processing_service_factory = payment_processing_service_factory

    async def process_payment(
        self, payment_reference_transfer: PaymentReferenceTransfer
    ) -> Payment | None:
        return await self._payment_processing_service_factory.create_processor().process_payment(
            payment_reference_transfer
        )
