from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from shared.Dto.context_transfer import ContextTransfer


class Transaction(Protocol):
    """Непрозрачный хэндл транзакции. Домен не знает его природу (ORM/сессия) —
    просто получает его из UnitOfWork и передаёт в репозитории-фабрики."""


class UnitOfWork(Protocol):
    """Порт единицы работы. Реализация (поверх конкретной ORM) — в infrastructure."""

    def begin(self) -> AbstractAsyncContextManager[Transaction]:
        """Открыть НОВУЮ короткую транзакцию (commit на выходе)."""
        ...

    def use_transaction(
        self, context_transfer: ContextTransfer | None
    ) -> AbstractAsyncContextManager[Transaction]:
        """Войти в транзакцию из контекста (enlisted), либо открыть свою короткую,
        если контекста/транзакции нет."""
        ...


class DuplicateKeyError(Exception):
    """Нарушение уникального ограничения. Доменное исключение — адаптер
    persistence маппит сюда специфичную ошибку ORM (напр. SQLAlchemy IntegrityError)."""
