"""PostgreSQL engine lifecycle and readiness checks."""

from collections.abc import AsyncIterator
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


def _async_database_url(settings: Settings) -> str:
    url = settings.DATABASE_URL.get_secret_value()
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        _async_database_url(settings),
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.DB_CONNECT_TIMEOUT_SECONDS},
    )


settings = get_settings()
engine = build_engine(settings)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


class DatabaseHealth(Protocol):
    async def is_ready(self) -> bool: ...


class SqlAlchemyDatabaseHealth:
    def __init__(self, database_engine: AsyncEngine) -> None:
        self._engine = database_engine

    async def is_ready(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except (OSError, TimeoutError):
            return False
        except Exception:  # SQLAlchemy/driver errors are intentionally not exposed by health APIs.
            return False


def get_database_health() -> DatabaseHealth:
    return SqlAlchemyDatabaseHealth(engine)
