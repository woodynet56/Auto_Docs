"""Collision-resistant public request folios."""

import secrets
from datetime import UTC, datetime

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_folio(now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    suffix = "".join(secrets.choice(ALPHABET) for _ in range(6))
    return f"REQ-{current:%Y%m%d}-{suffix}"
