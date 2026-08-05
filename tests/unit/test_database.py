from unittest.mock import AsyncMock, MagicMock

from app.core.config import Settings
from app.db.session import SqlAlchemyDatabaseHealth, _async_database_url


def test_render_postgresql_url_is_converted_for_async_driver() -> None:
    settings = Settings(DATABASE_URL="postgresql://user:synthetic@db.example/reaver")
    assert _async_database_url(settings).startswith("postgresql+psycopg://")


async def test_database_health_returns_true_after_select() -> None:
    connection = AsyncMock()
    context = AsyncMock()
    context.__aenter__.return_value = connection
    engine = MagicMock()
    engine.connect.return_value = context

    health = SqlAlchemyDatabaseHealth(engine)

    assert await health.is_ready() is True
    connection.execute.assert_awaited_once()


async def test_database_health_returns_false_on_driver_error() -> None:
    context = AsyncMock()
    context.__aenter__.side_effect = RuntimeError("synthetic driver failure")
    engine = MagicMock()
    engine.connect.return_value = context

    health = SqlAlchemyDatabaseHealth(engine)

    assert await health.is_ready() is False
