from modules.Backend.Payment.PaymentCreate.facade import PaymentCreateServiceFacade
from modules.Backend.Payment.PaymentProcessing.facade import (
    PaymentProcessingServiceFacade,
)
from modules.Backend.Payment.PaymentRepository.facade import (
    PaymentRepositoryServiceFacade,
)
from repository.entity.payment import Payment
from modules.Backend.Payment.PaymentCreate.Dto.payment_draft_transfer import (
    PaymentDraftTransfer,
)
from modules.Backend.Payment.PaymentProcessing.Dto.payment_reference_transfer import (
    PaymentReferenceTransfer,
)
from modules.Backend.Payment.PaymentRepository.Dto.payment_repository_transfer import (
    PaymentConditionsTransfer,
)


class PaymentFacade:
    """Публичный API модуля Payment. Только проксирует в сервисы (собираются в DI)."""

    def __init__(
        self,
        *,
        payment_repository_service_facade: PaymentRepositoryServiceFacade,
        payment_create_service_facade: PaymentCreateServiceFacade,
        payment_processing_service_facade: PaymentProcessingServiceFacade,
    ) -> None:
        self._payment_repository_service_facade = payment_repository_service_facade
        self._payment_create_service_facade = payment_create_service_facade
        self._payment_processing_service_facade = payment_processing_service_facade

    async def create_payment(
        self, payment_draft_transfer: PaymentDraftTransfer
    ) -> tuple[Payment, bool]:
        return await self._payment_create_service_facade.create_payment(
            payment_draft_transfer
        )

    async def find_payment(
        self, payment_conditions_transfer: PaymentConditionsTransfer
    ) -> Payment | None:
        return await self._payment_repository_service_facade.find_payment(
            payment_conditions_transfer
        )

    async def process_payment(
        self, payment_reference_transfer: PaymentReferenceTransfer
    ) -> Payment | None:
        return await self._payment_processing_service_facade.process_payment(
            payment_reference_transfer
        )
