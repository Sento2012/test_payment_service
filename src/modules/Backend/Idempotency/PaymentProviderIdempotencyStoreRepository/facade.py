from modules.Backend.Idempotency.PaymentProviderIdempotencyStoreRepository.factory import (
    PaymentProviderIdempotencyStoreRepositoryServiceFactory,
)
from repository.entity.idempotency_record import IdempotencyRecord
from modules.Backend.Idempotency.PaymentProviderIdempotencyStoreRepository.Dto.idempotency_transfer import (
    IdempotencyKeyTransfer,
    IdempotencyRecordDraftTransfer,
)


class PaymentProviderIdempotencyStoreRepositoryServiceFacade:
    def __init__(
        self,
        payment_provider_idempotency_store_repository_service_factory: PaymentProviderIdempotencyStoreRepositoryServiceFactory,
    ) -> None:
        self._payment_provider_idempotency_store_repository_service_factory = (
            payment_provider_idempotency_store_repository_service_factory
        )

    async def find_record(
        self, idempotency_key_transfer: IdempotencyKeyTransfer
    ) -> IdempotencyRecord | None:
        return await self._payment_provider_idempotency_store_repository_service_factory.create_repository_service().find_record(
            idempotency_key_transfer
        )

    async def get_or_create_record(
        self, idempotency_record_draft_transfer: IdempotencyRecordDraftTransfer
    ) -> IdempotencyRecord:
        return await self._payment_provider_idempotency_store_repository_service_factory.create_repository_service().get_or_create_record(
            idempotency_record_draft_transfer
        )
