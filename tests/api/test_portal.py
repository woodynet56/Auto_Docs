from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import app
from app.services.r2 import R2StorageClient


class Result:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.values)


class Session:
    def __init__(self, scalar_values: list[Any], documents: list[Any] | None = None) -> None:
        self.scalar_values = scalar_values
        self.documents = documents or []
        self.added: list[Any] = []
        self.commits = 0

    async def scalar(self, statement: Any) -> Any:
        return self.scalar_values.pop(0)

    async def scalars(self, statement: Any) -> Result:
        return Result(self.documents)

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1


async def api_client(application: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="https://test"
    ) as client:
        yield client


async def test_portal_rejects_missing_session(client: AsyncClient) -> None:
    response = await client.get("/portal")
    assert response.status_code == 401


async def test_redeem_sets_secure_cookie() -> None:
    grant = SimpleNamespace(last_accessed_at=None)
    session = Session([grant])

    async def session_override():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[get_session] = session_override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://test") as client:
            response = await client.get("/portal/acceso?token=" + "A" * 43, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/portal/verificar"
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
        assert response.headers["cache-control"] == "no-store, private"
    finally:
        app.dependency_overrides.clear()


async def test_verification_form_requires_pending_session() -> None:
    async with client_for_app() as test_client:
        response = await test_client.get("/portal/verificar")
    assert response.status_code == 401


def client_for_app() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://test")


async def test_otp_post_rejects_csrf_mismatch() -> None:
    session = Session([])

    async def session_override():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with client_for_app() as test_client:
            response = await test_client.post(
                "/portal/verificar",
                content="csrf=wrong&codigo=123456",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Cookie": "gr_portal_csrf=expected; gr_portal_session=" + "A" * 43,
                },
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_otp_post_rotates_authenticated_cookie(monkeypatch: Any) -> None:
    session = Session([])

    async def session_override():  # type: ignore[no-untyped-def]
        yield session

    rotated = "R" * 43
    monkeypatch.setattr("app.api.portal.verify_otp", AsyncMock(return_value=rotated))
    app.dependency_overrides[get_session] = session_override
    try:
        async with client_for_app() as test_client:
            response = await test_client.post(
                "/portal/verificar",
                content="csrf=expected&codigo=123456",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Cookie": "gr_portal_csrf=expected; gr_portal_session=" + "A" * 43,
                },
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert response.headers["location"] == "/portal"
        assert rotated in response.headers["set-cookie"]
        assert "Content-Security-Policy" in response.headers
    finally:
        app.dependency_overrides.clear()


async def test_portal_lists_only_available_documents() -> None:
    grant = SimpleNamespace(request_id="request", last_accessed_at=None)
    document = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        original_filename="resultado.pdf",
        storage_key="private/result.pdf",
    )
    session = Session([grant], [document])

    async def session_override():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[get_session] = session_override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://test") as client:
            response = await client.get(
                "/portal", headers={"Cookie": "gr_portal_session=" + "B" * 43}
            )
        assert response.status_code == 200
        assert "resultado.pdf" in response.text
        assert "no-store" in response.headers["cache-control"]
    finally:
        app.dependency_overrides.clear()


async def test_download_is_mediated_and_audited(monkeypatch: Any) -> None:
    grant = SimpleNamespace(id="grant", request_id="request", last_accessed_at=None)
    document = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        request_id="request",
        original_filename="resultado.pdf",
        storage_key="private/result.pdf",
        mime_type="application/pdf",
    )
    session = Session([grant, document])
    settings = Settings(
        R2_ENDPOINT_URL="https://example.invalid",
        R2_BUCKET_NAME="private",
        R2_ACCESS_KEY_ID=SecretStr("key"),
        R2_SECRET_ACCESS_KEY=SecretStr("secret"),
    )

    async def session_override():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(R2StorageClient, "get_private", AsyncMock(return_value=b"%PDF-1.7"))
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://test") as client:
            response = await client.get(
                "/portal/documentos/00000000-0000-0000-0000-000000000001",
                headers={"Cookie": "gr_portal_session=" + "C" * 43},
            )
        assert response.status_code == 200
        assert response.content == b"%PDF-1.7"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert len(session.added) == 1
    finally:
        app.dependency_overrides.clear()
