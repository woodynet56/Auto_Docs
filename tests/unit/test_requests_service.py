import uuid
from types import SimpleNamespace
from typing import cast

from pydantic import SecretStr

from app.repositories.requests import RequestRepository
from app.schemas.webhooks import InboundMessage
from app.services.requests import RequestCreationService, parse_intent


class FakeRepository:
    def __init__(self) -> None:
        self.created: dict[str, object] = {}
        self.notification: dict[str, object] = {}

    async def create(self, **kwargs: object) -> object:
        self.created = kwargs
        return SimpleNamespace(
            public_id="REQ-20260808-ABC234",
            service_type=kwargs["service_type"],
            identifier_masked="NAV****XXX",
            original_message=kwargs["original_message"],
            gestor=SimpleNamespace(phone_number="+525500000001"),
        )

    async def record_notification(self, **kwargs: object) -> None:
        self.notification = kwargs

    async def record_notification_failure(self, **kwargs: object) -> None:
        self.notification = {"failed": True, **kwargs}


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, recipient: str, text: str) -> str:
        self.sent.append((recipient, text))
        return f"wamid.{len(self.sent)}"


def message(text: str, sender: str = "525500000002") -> InboundMessage:
    return InboundMessage(
        provider_message_id="wamid.IN",
        sender_phone=sender,
        recipient_phone="525500000000",
        message_type="text",
        content=SecretStr(text),
    )


async def test_natural_message_creates_notifies_manager_and_confirms_client() -> None:
    repository, sender = FakeRepository(), FakeSender()
    service = RequestCreationService(cast(RequestRepository, repository), sender, "+525500000000")
    assert await service.process(
        message("Qué precio tiene una constancia este es NAVM12XXXX"), uuid.uuid4()
    )
    assert repository.created["service_type"] == "constancia_fiscal"
    assert repository.created["reference"] == "NAVM12XXXX"
    assert sender.sent[0][0] == "+525500000001"
    assert "REQ-20260808-ABC234" in sender.sent[0][1]
    assert sender.sent[1][0] == "+525500000002"


def test_invalid_or_missing_rfc_never_blocks_intake() -> None:
    intent = parse_intent("Necesito una constancia para Juan Pérez")
    assert intent.service_type == "constancia_fiscal"
    assert intent.reference is None


def test_typo_is_classified() -> None:
    assert parse_intent("Necesito una cata matrimonio").service_type == "acta_matrimonio"


async def test_non_text_is_ignored() -> None:
    service = RequestCreationService(
        cast(RequestRepository, FakeRepository()), FakeSender(), "+525500000000"
    )
    item = InboundMessage(
        provider_message_id="wamid.IN",
        sender_phone="525500000002",
        recipient_phone="525500000000",
        message_type="document",
    )
    assert not await service.process(item, uuid.uuid4())
