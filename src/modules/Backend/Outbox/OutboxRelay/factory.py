from config.groups import RelaySettings
from modules.Backend.Outbox.OutboxPaymentRepository.facade import (
    OutboxPaymentRepositoryServiceFacade,
)
from modules.Backend.Outbox.OutboxRelay.Business.outbox_relay import OutboxRelay
from modules.Backend.RabbitMq.facade import RabbitMqFacade
from shared.Port.persistence import UnitOfWork


class OutboxRelayServiceFactory:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        outbox_payment_repository_service_facade: OutboxPaymentRepositoryServiceFacade,
        rabbitmq_facade: RabbitMqFacade,
        relay_settings: RelaySettings,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._outbox_payment_repository_service_facade = (
            outbox_payment_repository_service_facade
        )
        self._rabbitmq_facade = rabbitmq_facade
        self._relay_settings = relay_settings

    def create_relay(self) -> OutboxRelay:
        return OutboxRelay(
            self._unit_of_work,
            self._outbox_payment_repository_service_facade,
            self._rabbitmq_facade,
            self._relay_settings,
        )
