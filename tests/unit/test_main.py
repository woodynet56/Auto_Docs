from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app, lifespan


async def test_lifespan_configures_logging_and_disposes_engine() -> None:
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock()
    with (
        patch("app.main.configure_logging") as configure_logging,
        patch("app.main.engine", new=fake_engine),
    ):
        async with lifespan(app):
            configure_logging.assert_called_once_with("INFO")

        fake_engine.dispose.assert_awaited_once()
