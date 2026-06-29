from modules.Backend.Payment.PaymentRepository.factory import (
    PaymentRepositoryServiceFactory,
)
from repository.entity.payment import Payment
from modules.Backend.Payment.PaymentCreate.Dto.payment_draft_transfer import (
    PaymentDraftTransfer,
)
from modules.Backend.Payment.PaymentRepository.Dto.payment_repository_transfer import (
    PaymentConditionsTransfer,
    PaymentUpdateTransfer,
)


class PaymentRepositoryServiceFacade:
    """Публичный API репозитория платежей. Делегирует чтение в Reader, создание —
    в Creator, обновление — в Updater."""

    def __init__(self, payment_repository_service_factory: PaymentRepositoryServiceFactory) -> None:
        self._payment_repository_service_factory = payment_repository_service_factory

    async def find_payment(
        self, payment_conditions_transfer: PaymentConditionsTransfer
    ) -> Payment | None:
        return await self._payment_repository_service_factory.create_reader().find_payment(
            payment_conditions_transfer
        )

    async def create_payment(
        self, payment_draft_transfer: PaymentDraftTransfer
    ) -> Payment:
        return await self._payment_repository_service_factory.create_creator().create_payment(
            payment_draft_transfer
        )

    async def update_payment(
        self, payment_update_transfer: PaymentUpdateTransfer
    ) -> None:
        await self._payment_repository_service_factory.create_updater().update_payment(
            payment_update_transfer
        )
