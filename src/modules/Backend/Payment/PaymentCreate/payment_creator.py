from modules.Backend.Outbox.OutboxPaymentRepository import (
    OutboxEventDraftTransfer,
    OutboxPaymentRepositoryService,
)
from modules.Backend.Payment.PaymentCreate.dto import PaymentDraftTransfer
from modules.Backend.Payment.PaymentRepository import (
    PaymentCreateTransfer,
    PaymentFindTransfer,
    PaymentRepositoryService,
)
from modules.Backend.RabbitMq.RabbitMqManagement.enum.routing_key import RoutingKey
from repository.entity.payment import Payment
from repository.enum.event_type import EventType
from shared.Dto import ContextTransfer
from shared.Port import DuplicateKeyError, UnitOfWork


class PaymentCreator:
    """Создание платежа + событие в outbox в ОДНОЙ транзакции.

    Сервис сам открывает транзакцию и кладёт её в контекст; репозиторий и outbox
    видят контекст и пишут в этой же транзакции (атомарно). Идемпотентность:
    перехват гонки по UNIQUE через доменное DuplicateKeyError.
    """

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        payment_repository_service: PaymentRepositoryService,
        outbox_repository_service: OutboxPaymentRepositoryService,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_repository_service = payment_repository_service
        self._outbox_repository_service = outbox_repository_service

    async def create_payment(
        self, payment_draft_transfer: PaymentDraftTransfer
    ) -> tuple[Payment, bool]:
        """Возвращает (payment, created). created=False — идемпотентное попадание.

        Без pre-SELECT: сразу пишем, уникальность Idempotency-Key проверит индекс.
        На дубль (DuplicateKeyError) — перечитываем существующий.
        """
        try:
            async with self._unit_of_work.begin() as tx:
                context = ContextTransfer(transaction=tx)  # обе записи в этой tx
                payment = await self._payment_repository_service.create_payment(
                    self._create_transfer(payment_draft_transfer, context)
                )
                await self._outbox_repository_service.create_outbox_event(
                    self._outbox_event(payment, context)
                )
            return payment, True
        except DuplicateKeyError:
            existing = await self._payment_repository_service.find_payment(
                PaymentFindTransfer(
                    idempotency_key=payment_draft_transfer.idempotency_key
                )
            )
            if existing is None:
                raise
            return existing, False

    def _create_transfer(
        self, payment_draft_transfer: PaymentDraftTransfer, context: ContextTransfer
    ) -> PaymentCreateTransfer:
        return PaymentCreateTransfer(
            idempotency_key=payment_draft_transfer.idempotency_key,
            amount=payment_draft_transfer.amount,
            currency=payment_draft_transfer.currency,
            webhook_url=payment_draft_transfer.webhook_url,
            description=payment_draft_transfer.description,
            meta=payment_draft_transfer.meta,
            provider=payment_draft_transfer.provider,
            context=context,
        )

    def _outbox_event(
        self, payment: Payment, context: ContextTransfer
    ) -> OutboxEventDraftTransfer:
        return OutboxEventDraftTransfer(
            event_type=EventType.PAYMENT_NEW,
            routing_key=RoutingKey.PAYMENTS_NEW,
            payment_id=payment.id,
            payload={"payment_id": str(payment.id)},  # consumer берёт данные из БД
            context=context,
        )
