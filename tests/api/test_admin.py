import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from starlette.requests import Request

from app.api.admin import dashboard, login, logout, reject_quarantined_document
from app.core.config import Settings
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus
from app.services.admin_identity import AdminIdentity, create_session, read_session


def settings() -> Settings:
    return Settings(ADMIN_API_TOKEN=SecretStr("strong-admin-token"))


def test_admin_session_is_encrypted_and_role_bound() -> None:
    configured = Settings(ADMIN_SESSION_KEY=SecretStr("x" * 32))
    token = create_session(configured, "subject", "admin@example.test", frozenset({"viewer"}))
    assert "admin@example.test" not in token
    identity = read_session(configured, token)
    assert identity.email == "admin@example.test"
    assert identity.roles == frozenset({"viewer"})


async def test_admin_login_dashboard_and_logout() -> None:
    configured = Settings(
        PUBLIC_BASE_URL="https://app.example.test",
        ADMIN_SESSION_KEY=SecretStr("x" * 32),
        OIDC_ISSUER_URL="https://identity.example.test",
        OIDC_CLIENT_ID="client",
    )
    login_response = await login(configured)
    assert login_response.status_code == 302
    assert login_response.headers["location"].startswith("https://identity.example.test")
    token = create_session(configured, "subject", "admin@example.test", frozenset({"viewer"}))
    request = Request({"type": "http", "headers": [(b"cookie", f"gr_admin={token}".encode())]})
    page = dashboard(request, configured)
    assert page.status_code == 200
    assert b"admin@example.test" in page.body
    redirect = dashboard(Request({"type": "http", "headers": []}), configured)
    assert redirect.status_code == 303
    logout_response = await logout()
    assert logout_response.status_code == 303


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

    identity = AdminIdentity("sub", "operator@example.test", frozenset({"operator"}), "csrf")
    request = Request({"type": "http", "headers": [(b"x-csrf-token", b"csrf")]})
    result = await reject_quarantined_document(item.id, request, session, identity)

    assert result == {"estado": DocumentStatus.REJECTED}
    assert item.status == DocumentStatus.REJECTED
    assert item.next_scan_at is None
    session.commit.assert_awaited_once()


async def test_admin_reject_handles_missing_and_final_document() -> None:
    session = AsyncMock()
    identity = AdminIdentity("sub", "operator@example.test", frozenset({"operator"}), "csrf")
    request = Request({"type": "http", "headers": [(b"x-csrf-token", b"csrf")]})
    session.scalar.return_value = None
    with pytest.raises(HTTPException) as missing:
        await reject_quarantined_document(uuid.uuid4(), request, session, identity)
    assert missing.value.status_code == 404

    item = quarantined()
    item.status = DocumentStatus.CLEAN
    session.scalar.return_value = item
    with pytest.raises(HTTPException) as conflict:
        await reject_quarantined_document(item.id, request, session, identity)
    assert conflict.value.status_code == 409
