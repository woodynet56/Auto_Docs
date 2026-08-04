import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.admin import reject_quarantined_document, require_admin
from app.core.config import Settings
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus


def settings() -> Settings:
    return Settings(ADMIN_API_TOKEN=SecretStr("strong-admin-token"))


def test_admin_requires_configured_matching_bearer() -> None:
    require_admin(settings(), "Bearer strong-admin-token")
    with pytest.raises(HTTPException) as error:
        require_admin(settings(), "Bearer wrong")
    assert error.value.status_code == 401
    with pytest.raises(HTTPException):
        require_admin(Settings(), None)


def quarantined() -> Document:
    return Document(
        id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        provider_media_id=uuid.uuid4().hex,
        storage_key="requests/test/file.pdf",
        original_filename="documento.pdf",
        mime_type="application/pdf",
        size_bytes=4,
        sha256="0" * 64,
        status=DocumentStatus.QUARANTINED,
        uploaded_by=uuid.uuid4(),
        expires_at=datetime.now(UTC),
        next_scan_at=datetime.now(UTC),
        scan_attempts=0,
    )


async def test_admin_can_reject_quarantined_document() -> None:
    item = quarantined()
    session = AsyncMock()
    session.scalar.return_value = item

    result = await reject_quarantined_document(item.id, session)

    assert result == {"estado": DocumentStatus.REJECTED}
    assert item.status == DocumentStatus.REJECTED
    assert item.next_scan_at is None
    session.commit.assert_awaited_once()


async def test_admin_reject_handles_missing_and_final_document() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    with pytest.raises(HTTPException) as missing:
        await reject_quarantined_document(uuid.uuid4(), session)
    assert missing.value.status_code == 404

    item = quarantined()
    item.status = DocumentStatus.CLEAN
    session.scalar.return_value = item
    with pytest.raises(HTTPException) as conflict:
        await reject_quarantined_document(item.id, session)
    assert conflict.value.status_code == 409
