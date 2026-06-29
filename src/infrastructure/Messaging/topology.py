"""Топология RabbitMQ: обменник, основная очередь, retry-очереди и DLQ.

Декларация разнесена на гранулярные функции — каждый воркер объявляет только те
очереди, которые использует (см. worker.Worker.declare_topology).

Схема retry/DLQ (RabbitMQ-native, возрастающий TTL по уровням):

    payments (direct) --payments.new--> payments.new   (consumer, prefetch=N)
    ошибка обработки -> payments.new.retry.{1..3} (x-message-ttl, dead-letter
                        обратно в payments -> payments.new); после 3 -> payments.new.dlq
"""
from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue

from config.settings import get_settings
from modules.Backend.RabbitMq.RabbitMqManagement.enum.exchange import Exchange
from modules.Backend.RabbitMq.RabbitMqManagement.enum.queue import Queue
from modules.Backend.RabbitMq.RabbitMqManagement.enum.routing_key import RoutingKey

_settings = get_settings()

PAYMENTS_EXCHANGE = RabbitExchange(
    Exchange.PAYMENTS, type=ExchangeType.DIRECT, durable=True
)

PAYMENTS_NEW_QUEUE = RabbitQueue(
    Queue.PAYMENTS_NEW,
    durable=True,
    routing_key=RoutingKey.PAYMENTS_NEW,
)

# retry-очереди: уровень i (1-based) с TTL из настроек; по истечении TTL
# сообщение возвращается в основной обменник на routing_key payments.new.
RETRY_QUEUES = [
    RabbitQueue(
        Queue.retry(level),
        durable=True,
        arguments={
            "x-message-ttl": ttl_ms,
            "x-dead-letter-exchange": Exchange.PAYMENTS,
            "x-dead-letter-routing-key": RoutingKey.PAYMENTS_NEW,
        },
    )
    for level, ttl_ms in enumerate(_settings.retry.ttls_ms, start=1)
]

DLQ_QUEUE = RabbitQueue(Queue.PAYMENTS_NEW_DLQ, durable=True)


async def declare_payments_new_queue(broker) -> None:
    """Обменник payments + основная очередь payments.new с биндингом."""
    exchange = await broker.declare_exchange(PAYMENTS_EXCHANGE)
    main_queue = await broker.declare_queue(PAYMENTS_NEW_QUEUE)
    await main_queue.bind(exchange, routing_key=RoutingKey.PAYMENTS_NEW)


async def declare_retry_queues(broker) -> None:
    for retry_queue in RETRY_QUEUES:
        await broker.declare_queue(retry_queue)


async def declare_dlq(broker) -> None:
    await broker.declare_queue(DLQ_QUEUE)
