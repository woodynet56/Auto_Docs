import hashlib
import hmac
import json
import uuid

from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.main import app
from app.repositories.webhook_events import get_webhook_event_repository
from app.schemas.webhooks import InboundMessage
from tests.unit.test_webhook_parser import synthetic_payload


class MemoryRepository:
    def __init__(self) -> None:
        self.ids: set[str] = set()

    async def add_if_new(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        assert correlation_id.version == 4
        if message.provider_message_id in self.ids:
            return False
        self.ids.add(message.provider_message_id)
        return True


def webhook_settings() -> Settings:
    return Settings(WA_VERIFY_TOKEN="verify-test", WA_APP_SECRET="app-test-secret")


def signed_headers(body: bytes) -> dict[str, str]:
    digest = hmac.new(b"app-test-secret", body, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={digest}", "content-type": "application/json"}


async def test_get_verification_returns_exact_challenge(client: AsyncClient) -> None:
    app.dependency_overrides[get_settings] = webhook_settings
    try:
        response = await client.get(
            "/webhooks/meta/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-test",
                "hub.challenge": "12345",
            },
        )
        assert response.status_code == 200
        assert response.text == "12345"
    finally:
        app.dependency_overrides.clear()


async def test_get_verification_rejects_invalid_token(client: AsyncClient) -> None:
    app.dependency_overrides[get_settings] = webhook_settings
    try:
        response = await client.get(
            "/webhooks/meta/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "123"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_post_is_authenticated_and_idempotent(client: AsyncClient) -> None:
    repository = MemoryRepository()
    app.dependency_overrides[get_settings] = webhook_settings
    app.dependency_overrides[get_webhook_event_repository] = lambda: repository
    body = json.dumps(synthetic_payload(), separators=(",", ":")).encode()
    try:
        first = await client.post(
            "/webhooks/meta/whatsapp", content=body, headers=signed_headers(body)
        )
        duplicate = await client.post(
            "/webhooks/meta/whatsapp", content=body, headers=signed_headers(body)
        )
        assert first.json() == {
            "accepted": 1,
            "duplicates": 0,
            "ignored": 0,
            "requests_created": 0,
            "documents_stored": 0,
            "confirmations_processed": 0,
        }
        assert duplicate.json() == {
            "accepted": 0,
            "duplicates": 1,
            "ignored": 0,
            "requests_created": 0,
            "documents_stored": 0,
            "confirmations_processed": 0,
        }
    finally:
        app.dependency_overrides.clear()


async def test_post_rejects_bad_signature_json_and_oversize(client: AsyncClient) -> None:
    app.dependency_overrides[get_settings] = webhook_settings
    app.dependency_overrides[get_webhook_event_repository] = MemoryRepository
    try:
        unsigned = await client.post("/webhooks/meta/whatsapp", content=b"{}")
        assert unsigned.status_code == 401
        malformed = b"not-json"
        bad_json = await client.post(
            "/webhooks/meta/whatsapp", content=malformed, headers=signed_headers(malformed)
        )
        assert bad_json.status_code == 400
        oversize = await client.post(
            "/webhooks/meta/whatsapp",
            content=b"{}",
            headers={**signed_headers(b"{}"), "content-length": "2000000"},
        )
        assert oversize.status_code == 413
    finally:
        app.dependency_overrides.clear()


async def test_post_ignores_non_message_event(client: AsyncClient) -> None:
    app.dependency_overrides[get_settings] = webhook_settings
    app.dependency_overrides[get_webhook_event_repository] = MemoryRepository
    body = b'{"object":"whatsapp_business_account","entry":[]}'
    try:
        response = await client.post(
            "/webhooks/meta/whatsapp", content=body, headers=signed_headers(body)
        )
        assert response.status_code == 200
        assert response.json()["ignored"] == 1
    finally:
        app.dependency_overrides.clear()
