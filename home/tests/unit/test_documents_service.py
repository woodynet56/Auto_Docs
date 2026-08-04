import uuid
from datetime import datetime

from app.repositories.documents import DocumentTarget
from app.schemas.webhooks import InboundMessage
from app.services.documents import DocumentIngestionService


class FakeRepository:
    def __init__(self, target: DocumentTarget | None) -> None:
        self.target = target
        self.recorded: dict[str, object] | None = None

    async def resolve_authorized_target(self, **kwargs: object) -> DocumentTarget | None:
        return self.target

    async def record(self, **kwargs: object) -> None:
        self.recorded = kwargs


class FakeDownloader:
    async def download(self, media_id: str) -> bytes:
        assert media_id == "media-1"
        return b"%PDF-1.7\nsynthetic"


class FakeStorage:
    def __init__(self) -> None:
        self.key = ""

    async def put_private(self, key: str, data: bytes, mime_type: str) -> None:
        assert data.startswith(b"%PDF")
        assert mime_type == "application/pdf"
        self.key = key


def media_message(*, sender: str = "5215555550101", caption: str | None = None) -> InboundMessage:
    return InboundMessage(
        provider_message_id="wamid-doc",
        sender_phone=sender,
        recipient_phone="5215555550199",
        message_type="document",
        media_id="media-1",
        media_filename="constancia.pdf",
        caption=caption,
    )


async def test_stores_authorized_document_by_caption() -> None:
    request_id = uuid.uuid4()
    repository = FakeRepository(DocumentTarget(request_id, "REQ-20260804-ABC123", uuid.uuid4()))
    storage = FakeStorage()
    service = DocumentIngestionService(repository, FakeDownloader(), storage, 10_000, 30)  # type: ignore[arg-type]
    stored = await service.process(media_message(caption="REQ-20260804-ABC123"), uuid.uuid4())
    assert stored is True
    assert storage.key.startswith(f"requests/{request_id}/")
    assert repository.recorded is not None
    assert repository.recorded["sha256"]
    assert isinstance(repository.recorded["expires_at"], datetime)


async def test_rejects_unassociated_or_unsupported_message() -> None:
    repository = FakeRepository(None)
    service = DocumentIngestionService(repository, FakeDownloader(), FakeStorage(), 10_000, 30)  # type: ignore[arg-type]
    assert await service.process(media_message(), uuid.uuid4()) is False
    text = media_message().model_copy(update={"message_type": "text", "media_id": None})
    assert await service.process(text, uuid.uuid4()) is False
