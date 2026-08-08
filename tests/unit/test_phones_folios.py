from datetime import UTC, datetime

import pytest

from app.services.folios import generate_folio
from app.services.phones import normalize_phone


def test_phone_normalization() -> None:
    assert normalize_phone("55 1234 5678") == "+525512345678"
    assert normalize_phone("+52 (55) 1234-5678") == "+525512345678"
    assert normalize_phone("15550002000") == "+15550002000"


@pytest.mark.parametrize("value", ["", "123", "+0123456789"])
def test_invalid_phone_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="E.164"):
        normalize_phone(value)


def test_folio_format_and_randomness() -> None:
    now = datetime(2026, 8, 4, tzinfo=UTC)
    first = generate_folio(now)
    second = generate_folio(now)
    assert first.startswith("REQ-20260804-")
    assert len(first) == 19
    assert first != second
