"""Outbox relay: публикует pending-события из payment_outbox в RabbitMQ.
Запуск: `python -m worker.relay.main`."""
import asyncio
import contextlib
import logging

from config.settings import get_settings
from di.container import get_container
from infrastructure.Messaging import declare_payments_new_queue, get_broker
from infrastructure.Persistence import dispose_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("relay")


async def _relay_once() -> int:
    return await get_container().outbox_relay().relay_pending_events()


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
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run())
