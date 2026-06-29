from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConsumerSettings:
    prefetch: int


@dataclass(frozen=True, slots=True)
class RelaySettings:
    batch_size: int
    poll_interval: float
    backoff_base: float
    backoff_cap: float


@dataclass(frozen=True, slots=True)
class RetrySettings:
    ttls_ms: tuple[int, ...]  # возрастающий TTL по уровням (RabbitMQ-native retry/DLQ)


@dataclass(frozen=True, slots=True)
class WebhookSettings:
    timeout: float


@dataclass(frozen=True, slots=True)
class GatewaySettings:
    min_delay: float
    max_delay: float
    success_rate: float  # 90% succeeded / 10% failed
