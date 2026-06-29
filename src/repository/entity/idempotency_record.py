from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class IdempotencyRecord:
    """Запись стора идемпотентности: ключ → сохранённое значение (результат операции).

    created_at задаётся при создании; источник истины — БД (подставляется при чтении)."""

    key: str
    value: dict
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
