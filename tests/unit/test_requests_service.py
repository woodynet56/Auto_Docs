import uuid
from dataclasses import dataclass
from typing import cast

from pydantic import SecretStr

from app.repositories.requests import RequestRepository
from app.schemas.webhooks import InboundMessage
from app.services.requests import RequestCreationService
from app.services.whatsapp import WhatsAppDeliveryError


@dataclass
class FakeRequest:
    public_id: str = "REQ-20260804-ABC234"
    identifier_masked: str = "COS*******7NA"


class FakeRepository:
    def __init__(self) -> None:
        self.created: dict[str, object] = {}
        self.notification: dict[str, object] = {}
        self.failure: dict[str, object] = {}

    async def create(self, **kwargs: object) -> FakeRequest:
        self.created = kwargs
        return FakeRequest()

    async def record_notification(self, **kwargs: object) -> None:
        self.notification = kwargs

    async def record_notification_failure(self, **kwargs: object) -> None:
        self.failure = kwargs


class FakeSender:
    def __init__(self) -> None:
        self.text = ""

    async def send_text(self, recipient: str, text: str) -> str:
        assert recipient == "+525500000001"
        self.text = text
        return "wamid.OUTBOUND_SYNTHETIC"


class FailingSender:
    async def send_text(self, recipient: str, text: str) -> str:
        del recipient, text
        raise WhatsAppDeliveryError("synthetic failure")


async def test_request_command_creates_notifies_and_records_message() -> None:
    repository = FakeRepository()
    sender = FakeSender()
    service = RequestCreationService(
        repository=cast(RequestRepository, repository),
        sender=sender,
        sender_phone="+525500000000",
        gestor_phone="+525500000001",
    )
    message = InboundMessage(
        provider_message_id="wamid.INBOUND_SYNTHETIC",
        sender_phone="525500000002",
        recipient_phone="525500000000",
        message_type="text",
        content=SecretStr("SOLICITUD: COSC8001137NA"),
    )
    correlation_id = uuid.uuid4()
    assert await service.process(message, correlation_id)
    assert repository.created["identifier"] == "COSC8001137NA"
    assert repository.created["inbound_message_id"] == "wamid.INBOUND_SYNTHETIC"
    assert "COS*******7NA" in sender.text
    assert "COSC8001137NA" not in sender.text
    assert repository.notification["provider_message_id"] == "wamid.OUTBOUND_SYNTHETIC"


async def test_non_request_message_is_ignored() -> None:
    service = RequestCreationService(
        repository=cast(RequestRepository, FakeRepository()),
        sender=FakeSender(),
        sender_phone="+525500000000",
        gestor_phone="+525500000001",
    )
    message = InboundMessage(
        provider_message_id="wamid.INBOUND_SYNTHETIC",
        sender_phone="525500000002",
        recipient_phone="525500000000",
        message_type="document",
    )
    assert not await service.process(message, uuid.uuid4())


async def test_delivery_failure_is_recorded_as_recoverable() -> None:
    repository = FakeRepository()
    service = RequestCreationService(
        repository=cast(RequestRepository, repository),
        sender=FailingSender(),
        sender_phone="+525500000000",
        gestor_phone="+525500000001",
    )
    public_id = await service.create_and_notify(
        client_phone="+525500000002",
        identifier="COSC8001137NA",
        inbound_message_id="wamid.INBOUND_SYNTHETIC",
        correlation_id=uuid.uuid4(),
    )
    assert public_id == "REQ-20260804-ABC234"
    assert repository.failure
    assert repository.notification == {}
