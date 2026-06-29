"""Прикладной DI-контейнер (композиционный корень).

Единая точка сборки зависимостей. Транзакциями управляет UnitOfWork: сервис
открывает короткую транзакцию вокруг DB-операций и кладёт её в ContextTransfer;
репозитории работают в ней (enlisted) либо открывают свою короткую, если контекст
пуст. Долгая логика выполняется вне транзакции. Модульные фасады только проксируют.
"""
from functools import lru_cache

from faststream.rabbit import RabbitBroker

from config.settings import Settings, get_settings
from infrastructure.Http.http_client_interface import HttpClientInterface
from infrastructure.Http.httpx_client import HttpxClient
from infrastructure.Messaging.broker import get_broker
from infrastructure.Messaging.rabbitmq_publisher import RabbitMqPublisher
from infrastructure.Persistence.database import get_session_factory
from infrastructure.Persistence.unit_of_work import SqlAlchemyUnitOfWork
from modules.Backend.Idempotency.facade import IdempotencyFacade
from modules.Backend.Idempotency.PaymentProviderIdempotencyStoreRepository.facade import (
    PaymentProviderIdempotencyStoreRepositoryServiceFacade,
)
from modules.Backend.Idempotency.PaymentProviderIdempotencyStoreRepository.factory import (
    PaymentProviderIdempotencyStoreRepositoryServiceFactory,
)
from modules.Backend.Outbox.facade import OutboxFacade
from modules.Backend.Outbox.OutboxPaymentRepository.facade import (
    OutboxPaymentRepositoryServiceFacade,
)
from modules.Backend.Outbox.OutboxPaymentRepository.factory import (
    OutboxPaymentRepositoryServiceFactory,
)
from modules.Backend.Outbox.OutboxRelay.facade import OutboxRelayServiceFacade
from modules.Backend.Outbox.OutboxRelay.factory import OutboxRelayServiceFactory
from modules.Backend.Notification.facade import NotificationFacade
from modules.Backend.Notification.WebhookNotificationService.facade import (
    WebhookNotificationServiceFacade,
)
from modules.Backend.Notification.WebhookNotificationService.factory import (
    WebhookNotificationServiceFactory,
)
from modules.Backend.Payment.facade import PaymentFacade
from modules.Backend.Payment.PaymentCreate.facade import PaymentCreateServiceFacade
from modules.Backend.Payment.PaymentCreate.factory import PaymentCreateServiceFactory
from modules.Backend.Payment.MockPaymentExecute.facade import (
    MockPaymentExecuteServiceFacade,
)
from modules.Backend.Payment.MockPaymentExecute.factory import (
    MockPaymentExecuteServiceFactory,
)
from modules.Backend.Payment.MockPaymentExecute.Plugin.mock_provider_execute_plugin import (
    MockProviderExecutePlugin,
)
from modules.Backend.Payment.PaymentExecute.facade import PaymentExecuteServiceFacade
from modules.Backend.Payment.PaymentExecute.factory import PaymentExecuteServiceFactory
from modules.Backend.Payment.PaymentExecute.Plugin.provider_execute_plugin_interface import (
    ProviderExecutePluginInterface,
)
from modules.Backend.Payment.PaymentProcessing.facade import (
    PaymentProcessingServiceFacade,
)
from modules.Backend.Payment.PaymentProcessing.factory import (
    PaymentProcessingServiceFactory,
)
from modules.Backend.Payment.PaymentRepository.facade import (
    PaymentRepositoryServiceFacade,
)
from modules.Backend.Payment.PaymentRepository.factory import (
    PaymentRepositoryServiceFactory,
)
from modules.Backend.RabbitMq.facade import RabbitMqFacade
from modules.Backend.RabbitMq.RabbitMqManagement.facade import (
    RabbitMqManagementServiceFacade,
)
from modules.Backend.RabbitMq.RabbitMqManagement.factory import (
    RabbitMqManagementServiceFactory,
)
from modules.Frontend.Request.facade import RequestFacade
from modules.Frontend.Request.RequestProcessingService.facade import (
    RequestProcessingServiceFacade,
)
from modules.Frontend.Request.RequestProcessingService.factory import (
    RequestProcessingServiceFactory,
)
from shared.Port.persistence import UnitOfWork


class Container:
    """DI-контейнер приложения."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._unit_of_work: UnitOfWork | None = None
        self._http_client: HttpClientInterface | None = None
        self._provider_plugins: list[ProviderExecutePluginInterface] | None = None

    @property
    def settings(self) -> Settings:
        return self._settings

    def broker(self) -> RabbitBroker:
        return get_broker()

    def unit_of_work(self) -> UnitOfWork:
        if self._unit_of_work is None:
            self._unit_of_work = SqlAlchemyUnitOfWork(get_session_factory())
        return self._unit_of_work

    def http_client(self) -> HttpClientInterface:
        if self._http_client is None:
            self._http_client = HttpxClient(self._settings.webhook.timeout)
        return self._http_client

    def idempotency_facade(self) -> IdempotencyFacade:
        payment_provider_idempotency_store_repository_service_facade = (
            PaymentProviderIdempotencyStoreRepositoryServiceFacade(
                PaymentProviderIdempotencyStoreRepositoryServiceFactory(
                    self.unit_of_work()
                )
            )
        )
        return IdempotencyFacade(
            payment_provider_idempotency_store_repository_service_facade=payment_provider_idempotency_store_repository_service_facade
        )

    def provider_plugins(self) -> list[ProviderExecutePluginInterface]:
        if self._provider_plugins is None:
            mock_payment_execute_service_facade = MockPaymentExecuteServiceFacade(
                MockPaymentExecuteServiceFactory(self._settings.gateway)
            )
            self._provider_plugins = [
                MockProviderExecutePlugin(mock_payment_execute_service_facade)
            ]
        return self._provider_plugins

    def rabbitmq_facade(self) -> RabbitMqFacade:
        rabbitmq_publisher = RabbitMqPublisher(self.broker())
        rabbitmq_management_service_facade = RabbitMqManagementServiceFacade(
            RabbitMqManagementServiceFactory(rabbitmq_publisher)
        )
        return RabbitMqFacade(
            rabbitmq_management_service_facade=rabbitmq_management_service_facade
        )

    def _outbox_repository_service(self) -> OutboxPaymentRepositoryServiceFacade:
        return OutboxPaymentRepositoryServiceFacade(
            OutboxPaymentRepositoryServiceFactory(self.unit_of_work())
        )

    def _outbox_relay_service(self) -> OutboxRelayServiceFacade:
        return OutboxRelayServiceFacade(
            OutboxRelayServiceFactory(
                self.unit_of_work(),
                self._outbox_repository_service(),
                self.rabbitmq_facade(),
                self._settings.relay,
            )
        )

    def _outbox_facade(self) -> OutboxFacade:
        return OutboxFacade(
            outbox_payment_repository_service_facade=self._outbox_repository_service(),
            outbox_relay_service_facade=self._outbox_relay_service(),
        )

    def outbox_relay_facade(self) -> OutboxFacade:
        return self._outbox_facade()

    def _payment_repository_service(self) -> PaymentRepositoryServiceFacade:
        return PaymentRepositoryServiceFacade(
            PaymentRepositoryServiceFactory(self.unit_of_work())
        )

    def payment_facade(self) -> PaymentFacade:
        payment_repository_service_facade = self._payment_repository_service()
        outbox_facade = self._outbox_facade()
        payment_create_service_facade = PaymentCreateServiceFacade(
            PaymentCreateServiceFactory(
                self.unit_of_work(), payment_repository_service_facade, outbox_facade
            )
        )
        payment_execute_service_facade = PaymentExecuteServiceFacade(
            PaymentExecuteServiceFactory(
                self.provider_plugins(), self.idempotency_facade()
            )
        )
        payment_processing_service_facade = PaymentProcessingServiceFacade(
            PaymentProcessingServiceFactory(
                self.unit_of_work(),
                payment_repository_service_facade,
                payment_execute_service_facade,
                self.notification_facade(),
            )
        )
        return PaymentFacade(
            payment_repository_service_facade=payment_repository_service_facade,
            payment_create_service_facade=payment_create_service_facade,
            payment_processing_service_facade=payment_processing_service_facade,
        )

    def notification_facade(self) -> NotificationFacade:
        webhook_notification_service_facade = WebhookNotificationServiceFacade(
            WebhookNotificationServiceFactory(
                self._payment_repository_service(), self.http_client()
            )
        )
        return NotificationFacade(
            webhook_notification_service_facade=webhook_notification_service_facade
        )

    def request_facade(self) -> RequestFacade:
        request_processing_service = RequestProcessingServiceFacade(
            RequestProcessingServiceFactory()
        )
        return RequestFacade(request_processing_service=request_processing_service)


@lru_cache
def get_container() -> Container:
    """Единый экземпляр контейнера на процесс (как get_settings)."""
    return Container()
