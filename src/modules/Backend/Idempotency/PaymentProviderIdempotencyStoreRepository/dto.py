from dataclasses import dataclass, field

from shared.Dto import ContextTransfer


@dataclass(slots=True)
class IdempotencyKeyTransfer:
    """Запрос записи стора идемпотентности по ключу (+ контекст вызова)."""

    key: str
    context: ContextTransfer = field(default_factory=ContextTransfer)


@dataclass(slots=True)
class IdempotencyRecordDraftTransfer:
    """Черновик записи стора идемпотентности (ключ + значение, + контекст вызова)."""

    key: str
    value: dict
    context: ContextTransfer = field(default_factory=ContextTransfer)
