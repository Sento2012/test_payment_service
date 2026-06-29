from modules.Backend.Notification.facade import NotificationFacade
from modules.Backend.Payment.PaymentExecute.facade import (
    PaymentExecuteServiceFacade,
)
from modules.Backend.Payment.PaymentProcessing.Business.payment_processor import (
    PaymentProcessor,
)
from modules.Backend.Payment.PaymentRepository.facade import (
    PaymentRepositoryServiceFacade,
)
from shared.Port.persistence import UnitOfWork


class PaymentProcessingServiceFactory:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        payment_repository_service_facade: PaymentRepositoryServiceFacade,
        payment_execute_service_facade: PaymentExecuteServiceFacade,
        notification_facade: NotificationFacade,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository_service_facade = payment_repository_service_facade
        self._payment_execute_service_facade = payment_execute_service_facade
        self._notification_facade = notification_facade

    def create_processor(self) -> PaymentProcessor:
        return PaymentProcessor(
            self._unit_of_work,
            self._payment_repository_service_facade,
            self._payment_execute_service_facade,
            self._notification_facade,
        )
