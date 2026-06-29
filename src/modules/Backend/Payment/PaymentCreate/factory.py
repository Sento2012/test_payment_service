from modules.Backend.Outbox.facade import OutboxFacade
from modules.Backend.Payment.PaymentCreate.Business.payment_creator import PaymentCreator
from modules.Backend.Payment.PaymentRepository.facade import (
    PaymentRepositoryServiceFacade,
)
from shared.Port.persistence import UnitOfWork


class PaymentCreateServiceFactory:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        payment_repository_service_facade: PaymentRepositoryServiceFacade,
        outbox_facade: OutboxFacade,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository_service_facade = payment_repository_service_facade
        self._outbox_facade = outbox_facade

    def create_creator(self) -> PaymentCreator:
        return PaymentCreator(
            self._unit_of_work,
            self._payment_repository_service_facade,
            self._outbox_facade,
        )
