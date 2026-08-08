import hashlib
import hmac
import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.core.config import Settings, get_settings
from app.db.session import get_database_health
from app.main import app
from app.repositories.webhook_events import get_webhook_event_repository
from app.schemas.webhooks import InboundMessage
from tests.unit.test_webhook_parser import synthetic_payload

pytestmark = pytest.mark.acceptance
scenarios("features/quality_gate.feature")


class DatabaseHealth:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    async def is_ready(self) -> bool:
        return self.ready


class MemoryWebhookRepository:
    def __init__(self) -> None:
        self.ids: set[str] = set()

    async def add_if_new(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        if message.provider_message_id in self.ids:
            return False
        self.ids.add(message.provider_message_id)
        return True


@dataclass
class Context:
    client: TestClient
    response: Any = None
    responses: list[Any] = field(default_factory=list)
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)


@pytest.fixture
def context() -> Iterator[Context]:
    app.dependency_overrides.clear()
    with TestClient(app, base_url="https://test") as client:
        yield Context(client)
    app.dependency_overrides.clear()


@given("que la aplicación se ejecuta en un entorno aislado con datos sintéticos")
def isolated_environment(context: Context) -> None:
    assert context.client.base_url.host == "test"


@given(parsers.parse("que PostgreSQL {availability}"))
def database_availability(context: Context, availability: str) -> None:
    ready = availability == "está disponible"
    app.dependency_overrides[get_database_health] = lambda: DatabaseHealth(ready)


@when("consulto el endpoint de disponibilidad")
def request_readiness(context: Context) -> None:
    context.response = context.client.get("/health/ready")


@then(parsers.parse("la respuesta HTTP es {status:d}"))
def response_status(context: Context, status: int) -> None:
    assert context.response.status_code == status


@then(parsers.parse('la dependencia "{dependency}" aparece como "{status}"'))
def dependency_status(context: Context, dependency: str, status: str) -> None:
    assert context.response.json()["dependencies"][dependency] == status


@then(parsers.parse('el estado de la aplicación es "{status}"'))
def application_status(context: Context, status: str) -> None:
    assert context.response.json()["status"] == status


def webhook_settings() -> Settings:
    return Settings(WA_VERIFY_TOKEN="verify-test", WA_APP_SECRET="app-test-secret")


@given("un webhook de Meta correctamente firmado")
def signed_webhook(context: Context) -> None:
    repository = MemoryWebhookRepository()
    app.dependency_overrides[get_settings] = webhook_settings
    app.dependency_overrides[get_webhook_event_repository] = lambda: repository
    context.body = json.dumps(synthetic_payload(), separators=(",", ":")).encode()
    digest = hmac.new(b"app-test-secret", context.body, hashlib.sha256).hexdigest()
    context.headers = {
        "X-Hub-Signature-256": f"sha256={digest}",
        "content-type": "application/json",
    }


@given("un webhook de Meta sin firma válida")
def unsigned_webhook(context: Context) -> None:
    app.dependency_overrides[get_settings] = webhook_settings
    context.body = b"{}"


@when(parsers.parse("envío el mismo webhook {count:d} veces"))
def send_repeated_webhook(context: Context, count: int) -> None:
    context.responses = [
        context.client.post(
            "/webhooks/meta/whatsapp", content=context.body, headers=context.headers
        )
        for _ in range(count)
    ]


@when("envío el webhook")
def send_webhook(context: Context) -> None:
    context.response = context.client.post(
        "/webhooks/meta/whatsapp", content=context.body, headers=context.headers
    )


@then(parsers.parse("el primer envío registra {count:d} mensaje aceptado"))
def first_accepted(context: Context, count: int) -> None:
    assert context.responses[0].json()["accepted"] == count


@then(parsers.parse("el segundo envío registra {count:d} duplicado"))
def second_duplicate(context: Context, count: int) -> None:
    assert context.responses[1].json()["duplicates"] == count


@given("que no tengo una sesión de portal")
def no_portal_session(context: Context) -> None:
    context.client.cookies.clear()


@when("consulto el portal del cliente")
def request_portal(context: Context) -> None:
    context.response = context.client.get("/portal")


@given(parsers.parse('que el número público del bot es "{phone}"'))
def public_bot_number(context: Context, phone: str, monkeypatch: pytest.MonkeyPatch) -> None:
    configured = Settings(PUBLIC_WHATSAPP_NUMBER=phone)
    monkeypatch.setattr("app.api.web.get_settings", lambda: configured)


@when("consulto la landing")
def request_landing(context: Context) -> None:
    context.response = context.client.get("/")


@then(parsers.parse('existe un vínculo a "{url}"'))
def link_exists(context: Context, url: str) -> None:
    assert f'href="{url}' in context.response.text
