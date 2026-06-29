import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from config.groups import (
    ConsumerSettings,
    GatewaySettings,
    RelaySettings,
    RetrySettings,
    WebhookSettings,
)
from config.yaml_config import YamlConfig, int_tuple

_CONFIG_YAML = Path(__file__).resolve().parent / "config.yaml"


@dataclass(frozen=True, slots=True)
class Settings:
    """Неизменяемая конфигурация сервиса, разбитая на группы.

    Доступы (БД, RabbitMQ, API-ключ) — из окружения; группы параметров — из
    секций config.yaml. Сборка — в get_settings().
    """

    database_url: str
    rabbitmq_url: str
    api_key: str
    consumer: ConsumerSettings
    relay: RelaySettings
    retry: RetrySettings
    webhook: WebhookSettings
    gateway: GatewaySettings


@lru_cache
def get_settings() -> Settings:
    cfg = YamlConfig(_CONFIG_YAML)
    consumer = cfg.section("consumer")
    relay = cfg.section("relay")
    retry = cfg.section("retry")
    webhook = cfg.section("webhook")
    gateway = cfg.section("gateway")

    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://payments:payments@postgres:5432/payments",
        ),
        rabbitmq_url=os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/"),
        api_key=os.environ.get("API_KEY", "secret-api-key"),
        consumer=ConsumerSettings(
            prefetch=consumer.value("prefetch", 10, int),
        ),
        relay=RelaySettings(
            batch_size=relay.value("batch_size", 100, int),
            poll_interval=relay.value("poll_interval", 1.0, float),
            backoff_base=relay.value("backoff_base", 2.0, float),
            backoff_cap=relay.value("backoff_cap", 60.0, float),
        ),
        retry=RetrySettings(
            ttls_ms=retry.value("ttls_ms", (1000, 5000, 25000), int_tuple),
        ),
        webhook=WebhookSettings(
            timeout=webhook.value("timeout", 5.0, float),
        ),
        gateway=GatewaySettings(
            min_delay=gateway.value("min_delay", 2.0, float),
            max_delay=gateway.value("max_delay", 5.0, float),
            success_rate=gateway.value("success_rate", 0.9, float),
        ),
    )
