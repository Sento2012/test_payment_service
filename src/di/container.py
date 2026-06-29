"""Прикладной DI-контейнер (композиционный корень).

Единая точка сборки сервисов. Фасадов/фабрик нет: сервис — это класс с логикой,
зависимости инжектятся конструктором здесь. Транзакциями управляет UnitOfWork: сервис
открывает короткую транзакцию вокруг DB-операций и кладёт её в ContextTransfer;
репозитории работают в ней (enlisted) либо открывают свою короткую. Долгая логика
выполняется вне транзакции.
"""
from functools import lru_cache

from config.settings import Settings, get_settings
from infrastructure.Http import HttpClientInterface, HttpxClient
from infrastructure.Messaging import RabbitMqPublisher, get_broker
from infrastructure.Persistence import SqlAlchemyUnitOfWork, get_session_factory
from modules.Backend.Idempotency.PaymentProviderIdempotencyStoreRepository import (
    PaymentProviderIdempotencyStoreRepositoryService,
)
from modules.Backend.Notification import WebhookNotificationSender
from modules.Backend.Outbox.OutboxPaymentRepository import (
    OutboxPaymentRepositoryService,
)
from modules.Backend.Outbox.OutboxRelay import OutboxRelay
from modules.Backend.Payment.MockPaymentExecute import (
    MockPaymentExecute,
    MockProviderExecutePlugin,
)
from modules.Backend.Payment.PaymentCreate import PaymentCreator
from modules.Backend.Payment.PaymentExecute import (
    PaymentExecutor,
    ProviderExecutePluginInterface,
)
from modules.Backend.Payment.PaymentProcessing import PaymentProcessor
from modules.Backend.Payment.PaymentRepository import PaymentRepositoryService
from repository.outbox_repository import OutboxRepository
from repository.payment_provider_idempotency_store_repository import (
    PaymentProviderIdempotencyStoreRepository,
)
from repository.payment_repository import PaymentRepository
from shared.Port import MessagePublisher, UnitOfWork


class Container:
    """DI-контейнер приложения: собирает сервисы и их зависимости."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._unit_of_work: UnitOfWork | None = None
        self._http_client: HttpClientInterface | None = None
        self._provider_plugins: list[ProviderExecutePluginInterface] | None = None

    @property
    def settings(self) -> Settings:
        return self._settings

    # --- инфраструктура (порты + адаптеры) ---

    def unit_of_work(self) -> UnitOfWork:
        if self._unit_of_work is None:
            self._unit_of_work = SqlAlchemyUnitOfWork(get_session_factory())
        return self._unit_of_work

    def http_client(self) -> HttpClientInterface:
        if self._http_client is None:
            self._http_client = HttpxClient(self._settings.webhook.timeout)
        return self._http_client

    def message_publisher(self) -> MessagePublisher:
        return RabbitMqPublisher(get_broker())

    # --- репозиторий-сервисы ---

    def payment_repository_service(self) -> PaymentRepositoryService:
        return PaymentRepositoryService(self.unit_of_work(), PaymentRepository())

    def outbox_repository_service(self) -> OutboxPaymentRepositoryService:
        return OutboxPaymentRepositoryService(self.unit_of_work(), OutboxRepository())

    def idempotency_store_service(
        self,
    ) -> PaymentProviderIdempotencyStoreRepositoryService:
        return PaymentProviderIdempotencyStoreRepositoryService(
            self.unit_of_work(), PaymentProviderIdempotencyStoreRepository()
        )

    # --- провайдеры оплаты (плагины) ---

    def provider_plugins(self) -> list[ProviderExecutePluginInterface]:
        if self._provider_plugins is None:
            self._provider_plugins = [
                MockProviderExecutePlugin(MockPaymentExecute(self._settings.gateway))
            ]
        return self._provider_plugins

    # --- бизнес-сервисы ---

    def payment_executor(self) -> PaymentExecutor:
        return PaymentExecutor(self.provider_plugins(), self.idempotency_store_service())

    def payment_creator(self) -> PaymentCreator:
        return PaymentCreator(
            self.unit_of_work(),
            self.payment_repository_service(),
            self.outbox_repository_service(),
        )

    def webhook_notification_sender(self) -> WebhookNotificationSender:
        return WebhookNotificationSender(
            self.payment_repository_service(), self.http_client()
        )

    def payment_processor(self) -> PaymentProcessor:
        return PaymentProcessor(
            self.unit_of_work(),
            self.payment_repository_service(),
            self.payment_executor(),
            self.webhook_notification_sender(),
        )

    def outbox_relay(self) -> OutboxRelay:
        return OutboxRelay(
            self.unit_of_work(),
            self.outbox_repository_service(),
            self.message_publisher(),
            self._settings.relay,
        )

    # --- presentation ---

    def api_router(self):
        # ленивый импорт: routes тянут get_container — отложенный импорт рвёт цикл
        from modules.Frontend.Request.RequestProcessingService.routes import payments

        return payments.router


@lru_cache
def get_container() -> Container:
    """Единый экземпляр контейнера на процесс (как get_settings)."""
    return Container()
