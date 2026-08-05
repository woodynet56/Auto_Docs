import time
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from starlette.requests import Request

from app.core.config import Settings
from app.services import admin_identity


def configured(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "ADMIN_SESSION_KEY": SecretStr("k" * 32),
        "OIDC_ISSUER_URL": "https://identity.example.test",
        "OIDC_CLIENT_ID": "client",
        "OIDC_CLIENT_SECRET": SecretStr("secret"),
    }
    values.update(overrides)
    return Settings.model_validate(values)


def test_state_round_trip_and_tampering() -> None:
    settings = configured()
    state = admin_identity.encode_state(settings, "nonce")
    assert admin_identity.decode_state(settings, state)["n"] == "nonce"
    with pytest.raises(HTTPException) as error:
        admin_identity.decode_state(settings, f"{state}x")
    assert error.value.status_code == 400


def test_state_expiration(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = configured()
    state = admin_identity.encode_state(settings, "nonce")
    monkeypatch.setattr(time, "time", lambda: 9_999_999_999)
    with pytest.raises(HTTPException):
        admin_identity.decode_state(settings, state)


def test_authorization_url_and_missing_configuration() -> None:
    url = admin_identity.authorization_url(configured(), "state", "https://app/callback")
    assert url.startswith("https://identity.example.test/authorize?")
    assert "state=state" in url
    with pytest.raises(RuntimeError):
        admin_identity.authorization_url(configured(OIDC_ISSUER_URL=None), "x", "https://app")


def test_session_rejects_missing_invalid_and_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = configured()
    with pytest.raises(HTTPException):
        admin_identity.read_session(settings, None)
    with pytest.raises(HTTPException):
        admin_identity.read_session(settings, "invalid")
    token = admin_identity.create_session(settings, "sub", "a@example.test", frozenset({"viewer"}))
    monkeypatch.setattr(time, "time", lambda: 9_999_999_999)
    with pytest.raises(HTTPException):
        admin_identity.read_session(settings, token)


def test_roles_and_csrf() -> None:
    settings = configured()
    token = admin_identity.create_session(settings, "sub", "a@example.test", frozenset({"viewer"}))
    request = Request({"type": "http", "headers": [(b"cookie", f"gr_admin={token}".encode())]})
    identity = admin_identity.require_role(request, settings, "viewer")
    with pytest.raises(HTTPException) as forbidden:
        admin_identity.require_role(request, settings, "operator")
    assert forbidden.value.status_code == 403
    valid = Request({"type": "http", "headers": [(b"x-csrf-token", identity.csrf.encode())]})
    admin_identity.validate_csrf(valid, identity)
    with pytest.raises(HTTPException):
        admin_identity.validate_csrf(Request({"type": "http", "headers": []}), identity)


class FakeResponse:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.data


class FakeClient:
    def __init__(self, claims: dict[str, object]) -> None:
        self.claims = claims
        self.post = AsyncMock(return_value=FakeResponse({"access_token": "access"}))
        self.get = AsyncMock(return_value=FakeResponse(claims))

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


async def test_exchange_code_maps_admin_group(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient({"sub": "s", "email": "admin@example.test", "groups": ["gestoria-admin"]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake)
    subject, email, roles = await admin_identity.exchange_code(
        configured(), "code", "https://app/callback"
    )
    assert (subject, email) == ("s", "admin@example.test")
    assert roles == frozenset({"viewer", "operator", "security_admin"})


async def test_exchange_code_rejects_incomplete_or_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeClient({"sub": "s", "email": "", "groups": []})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake)
    with pytest.raises(HTTPException):
        await admin_identity.exchange_code(configured(), "code", "https://app/callback")
    fake.claims = {"sub": "s", "email": "user@example.test", "groups": []}
    fake.get.return_value = FakeResponse(fake.claims)
    with pytest.raises(HTTPException):
        await admin_identity.exchange_code(configured(), "code", "https://app/callback")
