from modules.Backend.Outbox.OutboxPaymentRepository.Business.outbox_event_creator import (
    OutboxEventCreator,
)
from modules.Backend.Outbox.OutboxPaymentRepository.Business.outbox_event_reader import (
    OutboxEventReader,
)
from modules.Backend.Outbox.OutboxPaymentRepository.Business.outbox_event_updater import (
    OutboxEventUpdater,
)
from repository.outbox_repository import OutboxRepository
from shared.Port.persistence import UnitOfWork


class OutboxPaymentRepositoryServiceFactory:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work
        self._outbox_repository = OutboxRepository()

    def create_creator(self) -> OutboxEventCreator:
        return OutboxEventCreator(self._unit_of_work, self._outbox_repository)

    def create_reader(self) -> OutboxEventReader:
        return OutboxEventReader(self._unit_of_work, self._outbox_repository)

    def create_updater(self) -> OutboxEventUpdater:
        return OutboxEventUpdater(self._unit_of_work, self._outbox_repository)
