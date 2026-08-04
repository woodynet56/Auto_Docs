"""Authorized, validated and private inbound-document workflow."""

import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import PurePath
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.repositories.documents import DocumentRepository
from app.schemas.webhooks import InboundMessage
from app.services.document_validation import InvalidDocument, validate_document
from app.services.meta_media import MetaMediaClient
from app.services.r2 import R2StorageClient

FOLIO_PATTERN = re.compile(r"\bREQ-[0-9]{8}-[A-Z0-9]{6}\b")


class MediaDownloader(Protocol):
    async def download(self, media_id: str) -> bytes: ...


class PrivateStorage(Protocol):
    async def put_private(self, key: str, data: bytes, mime_type: str) -> None: ...


class DocumentProcessor(Protocol):
    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool: ...


class DisabledDocumentProcessor:
    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        del message, correlation_id
        return False


class DocumentIngestionService:
    def __init__(
        self,
        repository: DocumentRepository,
        downloader: MediaDownloader,
        storage: PrivateStorage,
        maximum_bytes: int,
        retention_days: int,
    ) -> None:
        self._repository = repository
        self._downloader = downloader
        self._storage = storage
        self._maximum_bytes = maximum_bytes
        self._retention_days = retention_days

    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        if message.message_type not in {"document", "image"} or not message.media_id:
            return False
        caption = message.caption.get_secret_value() if message.caption else ""
        match = FOLIO_PATTERN.search(caption.upper())
        target = await self._repository.resolve_authorized_target(
            sender_phone=f"+{message.sender_phone}",
            context_message_id=message.context_message_id,
            public_id=match.group(0) if match else None,
        )
        if target is None:
            return False
        data = await self._downloader.download(message.media_id)
        validated = validate_document(data, message.media_filename, self._maximum_bytes)
        digest = hashlib.sha256(data).hexdigest()
        key = f"requests/{target.request_id}/{uuid.uuid4().hex}{validated.extension}"
        await self._storage.put_private(key, data, validated.mime_type)
        expires_at = datetime.now(UTC) + timedelta(days=self._retention_days)
        filename = PurePath(message.media_filename or f"documento{validated.extension}").name
        try:
            await self._repository.record(
                target=target,
                media_id=message.media_id,
                storage_key=key,
                filename=filename,
                mime_type=validated.mime_type,
                size_bytes=len(data),
                sha256=digest,
                expires_at=expires_at,
                correlation_id=correlation_id,
            )
        except Exception:
            # R2 lifecycle removes the orphan no later than the configured retention period.
            raise
        return True


def get_document_processor(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentProcessor:
    endpoint = settings.R2_ENDPOINT_URL or ""
    bucket = settings.R2_BUCKET_NAME or ""
    access_key = settings.R2_ACCESS_KEY_ID.get_secret_value()
    secret_key = settings.R2_SECRET_ACCESS_KEY.get_secret_value()
    meta_token = settings.WA_ACCESS_TOKEN.get_secret_value()
    if not all((endpoint, bucket, access_key, secret_key, meta_token)):
        return DisabledDocumentProcessor()
    return DocumentIngestionService(
        repository=DocumentRepository(session),
        downloader=MetaMediaClient(
            settings.WA_API_VERSION, meta_token, settings.DOCUMENT_MAX_BYTES
        ),
        storage=R2StorageClient(endpoint, bucket, access_key, secret_key),
        maximum_bytes=settings.DOCUMENT_MAX_BYTES,
        retention_days=settings.DOCUMENT_RETENTION_DAYS,
    )


__all__ = [
    "DisabledDocumentProcessor",
    "DocumentIngestionService",
    "InvalidDocument",
    "get_document_processor",
]
