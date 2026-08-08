import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from pydantic import SecretStr

from app.db.models.enums import DeliveryStatus, DocumentStatus, RequestStatus
from app.schemas.webhooks import InboundMessage
from app.services.delivery import DeliveryService, DisabledDeliveryProcessor
from app.services.whatsapp import WhatsAppDeliveryError


class FakeResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.values)


class FakeSession:
    def __init__(self, request: Any, documents: list[Any], attempt: Any = None) -> None:
        self.scalar_values = [request, attempt, None]
        self.documents = documents
        self.added: list[Any] = []
        self.commits = 0

    async def scalar(self, statement: Any) -> Any:
        return self.scalar_values.pop(0)

    async def scalars(self, statement: Any) -> FakeResult:
        return FakeResult(self.documents)

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1


class FakeStorage:
    def presign_get(self, key: str, expires_seconds: int) -> str:
        return f"https://signed.invalid/{key}?ttl={expires_seconds}"


class FakeSender:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, recipient: str, text: str) -> str:
        self.sent.append((recipient, text))
        if self.fail:
            raise WhatsAppDeliveryError("synthetic failure")
        return "wamid.outbound.synthetic"


def service(session: FakeSession, sender: FakeSender, maximum_attempts: int = 3) -> DeliveryService:
    return DeliveryService(
        cast(Any, session),
        cast(Any, FakeStorage()),
        sender,
        "+5215555550199",
        maximum_attempts=maximum_attempts,
    )


def inbound(content: str = "CONFIRMAR REQ-20260804-ABC123") -> InboundMessage:
    return InboundMessage(
        provider_message_id="wamid.inbound.synthetic",
        sender_phone="5215555550101",
        recipient_phone="5215555550199",
        message_type="text",
        content=SecretStr(content),
    )


def objects() -> tuple[Any, Any]:
    request = SimpleNamespace(
        id=uuid.uuid4(),
        public_id="REQ-20260804-ABC123",
        status=RequestStatus.DOCUMENTS_RECEIVED,
        client=SimpleNamespace(phone_number="+5215555550102"),
        completed_at=None,
    )
    document = SimpleNamespace(
        storage_key="requests/synthetic.pdf",
        status=DocumentStatus.VALIDATED,
        delivered_at=None,
        delivery_message_id=None,
        expires_at=datetime.now(UTC),
    )
    return request, document


async def test_disabled_and_non_confirmation_are_ignored() -> None:
    assert not await DisabledDeliveryProcessor().process(inbound(), uuid.uuid4())
    processor = service(FakeSession(None, []), FakeSender())
    assert not await processor.process(inbound("HOLA"), uuid.uuid4())


async def test_unauthorized_confirmation_is_consumed() -> None:
    sender = FakeSender()
    processor = service(FakeSession(None, []), sender)
    assert await processor.process(inbound(), uuid.uuid4())
    assert not sender.sent


async def test_successful_delivery_completes_request() -> None:
    request, document = objects()
    session = FakeSession(request, [document])
    sender = FakeSender()
    processor = service(session, sender)
    assert await processor.process(inbound(), uuid.uuid4())
    assert request.status == RequestStatus.COMPLETED
    assert document.status == DocumentStatus.DELIVERED
    assert document.delivery_message_id == "wamid.outbound.synthetic"
    assert "REQ-20260804-ABC123" in sender.sent[0][1]
    assert len(sender.sent) == 2
    assert "Código de verificación" in sender.sent[1][1]
    assert "portal/acceso" not in sender.sent[1][1]
    assert session.commits == 2


async def test_failure_is_retried_then_final() -> None:
    request, document = objects()
    attempt = SimpleNamespace(
        status=DeliveryStatus.PENDING,
        attempt_count=0,
        next_attempt_at=None,
        last_error_code=None,
        provider_message_id=None,
    )
    session = FakeSession(request, [document], attempt)
    processor = service(session, FakeSender(fail=True), maximum_attempts=2)
    assert await processor.process(inbound(), uuid.uuid4())
    assert attempt.status == DeliveryStatus.PENDING
    request.status = RequestStatus.DOCUMENTS_RECEIVED
    session.scalar_values = [request, attempt, None]
    assert await processor.process(inbound(), uuid.uuid4())
    assert attempt.status == DeliveryStatus.FAILED
    assert attempt.last_error_code == "meta_delivery_failed"


async def test_missing_documents_is_audited() -> None:
    request, _ = objects()
    session = FakeSession(request, [])
    processor = service(session, FakeSender())
    assert await processor.process(inbound(), uuid.uuid4())
    assert session.commits == 1


class RetrySession(FakeSession):
    def __init__(self, attempt: Any, request: Any, documents: list[Any]) -> None:
        super().__init__(request, documents)
        self.attempt = attempt
        self.scalar_values = [request, None]
        self.result_values = [[attempt], documents]

    async def scalars(self, statement: Any) -> FakeResult:
        return FakeResult(self.result_values.pop(0))


async def test_due_retry_is_delivered_once() -> None:
    request, document = objects()
    request.status = RequestStatus.AWAITING_CONFIRMATION
    attempt = SimpleNamespace(
        request_id=request.id,
        correlation_id=uuid.uuid4(),
        status=DeliveryStatus.PENDING,
        attempt_count=1,
        next_attempt_at=datetime.now(UTC),
        last_error_code=None,
        provider_message_id=None,
    )
    session = RetrySession(attempt, request, [document])
    processor = service(session, FakeSender())
    assert await processor.retry_due() == 1
    assert attempt.status == DeliveryStatus.SENT
    assert request.status == RequestStatus.COMPLETED


async def test_due_retry_without_deliverable_request_is_failed() -> None:
    attempt = SimpleNamespace(
        request_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        status=DeliveryStatus.PENDING,
        attempt_count=1,
        next_attempt_at=datetime.now(UTC),
        last_error_code=None,
    )
    session = RetrySession(attempt, None, [])
    processor = service(session, FakeSender())
    assert await processor.retry_due() == 0
    assert attempt.status == DeliveryStatus.FAILED
    assert attempt.last_error_code == "request_not_deliverable"
