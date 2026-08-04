import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_reject_non_postgresql_database() -> None:
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="sqlite:///unsafe.db")


def test_database_secret_is_redacted() -> None:
    settings = Settings(DATABASE_URL="postgresql://user:secret@db.example/reaver")
    assert "secret" not in str(settings.DATABASE_URL)


@pytest.mark.parametrize("number", ["+525512345678", "abc12345", "１２３４５６７８"])
def test_settings_reject_invalid_public_whatsapp_number(number: str) -> None:
    with pytest.raises(ValidationError):
        Settings(PUBLIC_WHATSAPP_NUMBER=number)


def test_settings_accept_public_whatsapp_digits() -> None:
    settings = Settings(PUBLIC_WHATSAPP_NUMBER="525512345678")
    assert settings.PUBLIC_WHATSAPP_NUMBER == "525512345678"
