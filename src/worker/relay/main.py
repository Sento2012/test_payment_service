"""Outbox relay: публикует pending-события из payment_outbox в RabbitMQ.
Запуск: `python -m worker.relay.main`."""
import asyncio
import logging

from config.settings import get_settings
from di.container import get_container
from infrastructure.Messaging.broker import get_broker
from infrastructure.Messaging.topology import declare_payments_new_queue
from infrastructure.Persistence.database import dispose_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("relay")


async def _relay_once() -> int:
    return await get_container().outbox_relay_facade().relay_pending_events()


async def run() -> None:
    settings = get_settings()
    broker = get_broker()
    await broker.connect()
    await declare_payments_new_queue(broker)
    logger.info(
        "relay started (poll=%ss, batch=%s)",
        settings.relay.poll_interval, settings.relay.batch_size,
    )
    try:
        while True:
            try:
                processed = await _relay_once()
            except Exception:  # noqa: BLE001 — цикл relay не должен падать целиком
                logger.exception("relay iteration failed")
                processed = 0
            # есть бэклог — продолжаем без паузы; пусто — ждём poll-интервал
            if processed == 0:
                await asyncio.sleep(settings.relay.poll_interval)
    finally:
        await broker.close()
        await dispose_engine()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
