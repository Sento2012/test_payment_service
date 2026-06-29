from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.Dto.context_transfer import ContextTransfer
from shared.Port.persistence import DuplicateKeyError


class SqlAlchemyUnitOfWork:
    """Реализация порта shared.Port.persistence.UnitOfWork поверх SQLAlchemy.

    Транзакция короткая: commit на выходе, rollback при исключении. IntegrityError
    маппится в доменное DuplicateKeyError. AsyncSession играет роль Transaction-хэндла.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[AsyncSession]:
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise DuplicateKeyError(str(exc.orig)) from exc
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def use_transaction(
        self, context_transfer: ContextTransfer | None
    ) -> AsyncIterator[AsyncSession]:
        """Enlisted-режим (в контексте есть транзакция) — отдаём её хэндл, commit
        делает владелец. Иначе открываем свою короткую транзакцию."""
        if context_transfer is not None and context_transfer.transaction is not None:
            yield context_transfer.transaction
        else:
            async with self.begin() as session:
                yield session
