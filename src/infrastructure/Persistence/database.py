from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        # consumer держит FOR UPDATE-лок (и коннект) на время вызова шлюза (2–5с),
        # параллельно до prefetch платежей + заблокированные дубли-«ждуны» →
        # размер пула привязываем к prefetch с запасом.
        prefetch = settings.consumer.prefetch
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
            pool_size=prefetch,
            max_overflow=prefetch,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
