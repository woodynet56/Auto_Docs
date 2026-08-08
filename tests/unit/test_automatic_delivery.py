import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import DeliveryStatus, DocumentStatus, RequestStatus
from app.services.automatic_delivery import AutomaticDeliveryService
from app.services.r2 import R2StorageClient
from app.services.whatsapp import WhatsAppDeliveryError


class Result:
    def __init__(self, value: Any) -> None:
        self.value = value

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.value)


class Session:
    def __init__(self, document: Any, request: Any, attempt: Any = None) -> None:
        self.document, self.request, self.attempt = document, request, attempt
        self.added: list[Any] = []
        self.scalar_calls = 0

    async def scalars(self, query: Any) -> Result:
        del query
        return Result([self.document])

    async def scalar(self, query: Any) -> Any:
        del query
        self.scalar_calls += 1
        return self.request if self.scalar_calls == 1 else self.attempt

    def add(self, item: Any) -> None:
        self.added.append(item)
        if item.__class__.__name__ == "DeliveryAttempt":
            self.attempt = item

    async def commit(self) -> None:
        return None


class Storage:
    def presign_get(self, key: str, ttl: int) -> str:
        assert key == "requests/file.pdf"
        assert ttl == 600
        return "https://private.invalid/file"


class Sender:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.documents: list[tuple[str, str]] = []

    async def send_document(self, recipient: str, link: str, filename: str, caption: str) -> str:
        del filename, caption
        if self.fail:
            raise WhatsAppDeliveryError("synthetic")
        self.documents.append((recipient, link))
        return "wamid.DOC"

    async def send_text(self, recipient: str, text: str) -> str:
        del recipient, text
        return "wamid.TEXT"


def objects() -> tuple[Any, Any]:
    document = SimpleNamespace(
        id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        status=DocumentStatus.CLEAN,
        storage_key="requests/file.pdf",
        original_filename="file.pdf",
        delivered_at=None,
        delivery_message_id=None,
    )
    request = SimpleNamespace(
        id=document.request_id,
        status=RequestStatus.ASSIGNED,
        client=SimpleNamespace(phone_number="+525500000099"),
        public_id="REQ-20260808-ABC234",
        completed_at=None,
    )
    return document, request


def service(session: Session, sender: Sender) -> AutomaticDeliveryService:
    return AutomaticDeliveryService(
        cast(AsyncSession, session), cast(R2StorageClient, Storage()), sender
    )


async def test_first_clean_document_is_delivered_and_completes_request() -> None:
    document, request = objects()
    session, sender = Session(document, request), Sender()
    count = await service(session, sender).process_due()
    assert count == 1
    assert sender.documents[0][0] == request.client.phone_number
    assert request.status == RequestStatus.COMPLETED
    assert document.status == DocumentStatus.DELIVERED


async def test_existing_sent_attempt_rejects_second_document() -> None:
    document, request = objects()
    attempt = SimpleNamespace(status=DeliveryStatus.SENT)
    count = await service(Session(document, request, attempt), Sender()).process_due()
    assert count == 0
    assert document.status == DocumentStatus.REJECTED


async def test_meta_failure_schedules_retry_without_completing() -> None:
    document, request = objects()
    session = Session(document, request)
    count = await service(session, Sender(fail=True)).process_due()
    assert count == 0
    assert request.status == RequestStatus.ASSIGNED
    assert session.attempt.status == DeliveryStatus.PENDING
    assert session.attempt.next_attempt_at > datetime.now(UTC)
