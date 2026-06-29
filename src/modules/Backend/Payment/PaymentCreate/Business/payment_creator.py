from modules.Backend.Outbox.facade import OutboxFacade
from modules.Backend.Payment.PaymentRepository.facade import (
    PaymentRepositoryServiceFacade,
)
from repository.entity.payment import Payment
from repository.enum.event_type import EventType
from modules.Backend.RabbitMq.RabbitMqManagement.enum.routing_key import RoutingKey
from shared.Dto.context_transfer import ContextTransfer
from modules.Backend.Outbox.OutboxPaymentRepository.Dto.outbox_event_transfer import OutboxEventDraftTransfer
from modules.Backend.Payment.PaymentCreate.Dto.payment_draft_transfer import (
    PaymentDraftTransfer,
)
from modules.Backend.Payment.PaymentRepository.Dto.payment_repository_transfer import (
    PaymentConditionsTransfer,
)
from shared.Port.persistence import DuplicateKeyError, UnitOfWork


class PaymentCreator:
    """Создание платежа + событие в outbox в ОДНОЙ транзакции.

    Сервис сам открывает транзакцию и кладёт её в контекст; репозиторий и outbox
    видят контекст и пишут в этой же транзакции (атомарно). Идемпотентность:
    перехват гонки по UNIQUE через доменное DuplicateKeyError.
    """

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        payment_repository_service_facade: PaymentRepositoryServiceFacade,
        outbox_facade: OutboxFacade,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository_service_facade = payment_repository_service_facade
        self._outbox_facade = outbox_facade

    def _outbox_event(
        self, payment: Payment, context_transfer: ContextTransfer
    ) -> OutboxEventDraftTransfer:
        return OutboxEventDraftTransfer(
            event_type=EventType.PAYMENT_NEW,
            routing_key=RoutingKey.PAYMENTS_NEW,
            payment_id=payment.id,
            payload={"payment_id": str(payment.id)},  # consumer берёт данные из БД
            context=context_transfer,
        )

    async def create_payment(
        self, payment_draft_transfer: PaymentDraftTransfer
    ) -> tuple[Payment, bool]:
        """Возвращает (payment, created). created=False — идемпотентное попадание.

        Без pre-SELECT: сразу пишем, уникальность Idempotency-Key проверит индекс.
        На дубль (DuplicateKeyError) — перечитываем существующий.
        """
        try:
            async with self._unit_of_work.begin() as tx:
                payment_draft_transfer.context.transaction = tx  # обе записи в этой tx
                payment = await self._payment_repository_service_facade.create_payment(
                    payment_draft_transfer
                )
                await self._outbox_facade.create_outbox_event(
                    self._outbox_event(payment, payment_draft_transfer.context)
                )
            return payment, True
        except DuplicateKeyError:
            payment = await self._payment_repository_service_facade.find_payment(
                PaymentConditionsTransfer(
                    idempotency_key=payment_draft_transfer.idempotency_key
                )
            )
            if payment is None:
                raise
            return payment, False
