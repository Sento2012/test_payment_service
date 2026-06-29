from modules.Backend.Payment.PaymentRepository.Business.payment_creator import (
    PaymentCreator,
)
from modules.Backend.Payment.PaymentRepository.Business.payment_reader import (
    PaymentReader,
)
from modules.Backend.Payment.PaymentRepository.Business.payment_updater import (
    PaymentUpdater,
)
from repository.payment_repository import PaymentRepository
from shared.Port.persistence import UnitOfWork


class PaymentRepositoryServiceFactory:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository = PaymentRepository()

    def create_reader(self) -> PaymentReader:
        return PaymentReader(self._unit_of_work, self._payment_repository)

    def create_creator(self) -> PaymentCreator:
        return PaymentCreator(self._unit_of_work, self._payment_repository)

    def create_updater(self) -> PaymentUpdater:
        return PaymentUpdater(self._unit_of_work, self._payment_repository)
