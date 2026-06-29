import asyncio
import logging
from datetime import UTC, datetime, timedelta

from config.groups import RelaySettings
from modules.Backend.Outbox.OutboxPaymentRepository import (
    GetPendingEventsWithLockTransfer,
    OutboxEventUpdateTransfer,
    OutboxPaymentRepositoryService,
)
from repository.entity.outbox_event import OutboxEvent
from repository.enum.outbox_status import OutboxStatus
from shared.Dto import ContextTransfer, PublishEventTransfer
from shared.Port import MessagePublisher, UnitOfWork

logger = logging.getLogger(__name__)


class OutboxRelay:
    """Перекладывает события из payment_outbox в RabbitMQ (at-least-once).

    Одна итерация = одна транзакция (открывает сам relay и кладёт в контекст):
    fetch pending (FOR UPDATE SKIP LOCKED) → publish → update. Блокировка строк
    на время публикации намеренна (at-least-once при нескольких relay-инстансах).
    """

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        outbox_repository_service: OutboxPaymentRepositoryService,
        message_publisher: MessagePublisher,
        relay_settings: RelaySettings,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._outbox_repository_service = outbox_repository_service
        self._message_publisher = message_publisher
        self._relay_settings = relay_settings

    async def relay_pending_events(self) -> int:
        async with self._unit_of_work.begin() as tx:
            context_transfer = ContextTransfer(transaction=tx)
            outbox_events = (
                await self._outbox_repository_service.get_pending_events_with_lock(
                    GetPendingEventsWithLockTransfer(
                        limit=self._relay_settings.batch_size, context=context_transfer
                    )
                )
            )
            # публикация — независимые сетевые вызовы в RabbitMQ, шлём всю пачку
            # конкурентно; ошибку каждого получаем отдельно (return_exceptions)
            publish_results = await asyncio.gather(
                *(self._publish_event(outbox_event) for outbox_event in outbox_events),
                return_exceptions=True,
            )
            # апдейты НЕ параллелим: они идут в одной транзакции/сессии,
            # а AsyncSession не допускает конкурентных запросов — пишем последовательно
            for outbox_event, publish_result in zip(
                outbox_events, publish_results, strict=True
            ):
                if isinstance(publish_result, Exception):
                    outbox_event.attempts += 1
                    outbox_event.last_error = str(publish_result)
                    if outbox_event.attempts >= self._relay_settings.max_attempts:
                        # «ядовитое» событие: не ретраим бесконечно — паркуем в FAILED
                        # (нужен разбор/алерт; из выборки pending больше не попадёт)
                        outbox_event.status = OutboxStatus.FAILED
                        logger.error(
                            "outbox event %s parked as FAILED after %s attempts: %s",
                            outbox_event.id, outbox_event.attempts, publish_result,
                        )
                    else:
                        outbox_event.available_at = self._backoff_until(
                            outbox_event.attempts
                        )
                        logger.warning(
                            "Failed to publish outbox event %s (attempt %s/%s): %s",
                            outbox_event.id,
                            outbox_event.attempts,
                            self._relay_settings.max_attempts,
                            publish_result,
                        )
                else:
                    outbox_event.status = OutboxStatus.PUBLISHED
                    outbox_event.published_at = datetime.now(UTC)
                await self._outbox_repository_service.update_outbox_event(
                    OutboxEventUpdateTransfer(
                        outbox_event=outbox_event, context=context_transfer
                    )
                )
            return len(outbox_events)

    async def _publish_event(self, outbox_event: OutboxEvent) -> None:
        await self._message_publisher.publish_event(
            PublishEventTransfer(
                routing_key=outbox_event.routing_key,
                payload=outbox_event.payload,
                message_id=str(outbox_event.id),
            )
        )

    def _backoff_until(self, attempts: int) -> datetime:
        delay = min(
            self._relay_settings.backoff_base ** attempts,
            self._relay_settings.backoff_cap,
        )
        return datetime.now(UTC) + timedelta(seconds=delay)
