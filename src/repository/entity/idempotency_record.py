from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class IdempotencyRecord:
    """Запись стора идемпотентности: ключ → сохранённое значение (результат операции)."""

    key: str
    value: dict
    created_at: datetime | None = None
