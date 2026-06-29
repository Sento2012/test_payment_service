import logging
from uuid import UUID

from faststream import FastStream
from faststream.rabbit import RabbitMessage

from config.settings import get_settings
from di.container import get_container
from infrastructure.Messaging.broker import get_broker
from infrastructure.Messaging.topology import (
    PAYMENTS_EXCHANGE,
    PAYMENTS_NEW_QUEUE,
    declare_dlq,
    declare_payments_new_queue,
    declare_retry_queues,
)
from infrastructure.Persistence.database import dispose_engine
from modules.Backend.RabbitMq.RabbitMqManagement.enum.message_header import MessageHeader
from modules.Backend.RabbitMq.RabbitMqManagement.enum.queue import Queue
from modules.Backend.Payment.PaymentProcessing.Dto.payment_reference_transfer import PaymentReferenceTransfer
from shared.Dto.rabbitmq_transfer import PublishToQueueTransfer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("consumer")

settings = get_settings()
broker = get_broker()
app = FastStream(broker)


@app.after_startup
async def after_startup() -> None:
    await declare_payments_new_queue(broker)
    await declare_retry_queues(broker)
    await declare_dlq(broker)


@app.on_shutdown
async def on_shutdown() -> None:
    await dispose_engine()


async def _route_to_retry_or_dlq(body: dict, attempt: int, exc: Exception) -> None:
    """RabbitMQ-native retry: republish в retry-очередь уровня (возрастающий TTL),
    после исчерпания попыток — в DLQ. Исходное сообщение ack'ается (штатный return)."""
    rabbitmq_facade = get_container().rabbitmq_facade()
    next_attempt = attempt + 1
    max_retries = len(settings.retry.ttls_ms)

    if next_attempt <= max_retries:
        target = Queue.retry(next_attempt)
        logger.warning(
            "payment %s processing failed (attempt %s/%s): %s -> %s",
            body.get("payment_id"), attempt, max_retries, exc, target,
        )
        await rabbitmq_facade.publish_to_queue(
            PublishToQueueTransfer(
                queue_name=target,
                payload=body,
                headers={MessageHeader.ATTEMPT: next_attempt},
            )
        )
    else:
        logger.error(
            "payment %s exhausted %s retries -> DLQ: %s",
            body.get("payment_id"), max_retries, exc,
        )
        await rabbitmq_facade.publish_to_queue(
            PublishToQueueTransfer(
                queue_name=Queue.PAYMENTS_NEW_DLQ,
                payload=body,
                headers={MessageHeader.ATTEMPT: next_attempt, "x-error": str(exc)[:500]},
            )
        )


@broker.subscriber(PAYMENTS_NEW_QUEUE, PAYMENTS_EXCHANGE, retry=False)
async def on_payment_new(body: dict, msg: RabbitMessage) -> None:
    payment_id = UUID(body["payment_id"])
    attempt = int((msg.headers or {}).get(MessageHeader.ATTEMPT, 0))
    try:
        payment_reference_transfer = PaymentReferenceTransfer(payment_id=payment_id)
        await get_container().payment_facade().process_payment(
            payment_reference_transfer
        )
    except Exception as exc:  # noqa: BLE001 — любую ошибку обработки уводим в retry/DLQ
        await _route_to_retry_or_dlq(body, attempt, exc)
