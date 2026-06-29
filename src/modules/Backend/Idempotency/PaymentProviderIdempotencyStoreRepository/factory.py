from modules.Backend.Idempotency.PaymentProviderIdempotencyStoreRepository.Business.payment_provider_idempotency_store_repository_service import (
    PaymentProviderIdempotencyStoreRepositoryService,
)
from repository.payment_provider_idempotency_store_repository import PaymentProviderIdempotencyStoreRepository
from shared.Port.persistence import UnitOfWork


class PaymentProviderIdempotencyStoreRepositoryServiceFactory:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work
        self._payment_provider_idempotency_store_repository = PaymentProviderIdempotencyStoreRepository()

    def create_repository_service(self) -> PaymentProviderIdempotencyStoreRepositoryService:
        return PaymentProviderIdempotencyStoreRepositoryService(
            self._unit_of_work, self._payment_provider_idempotency_store_repository
        )
