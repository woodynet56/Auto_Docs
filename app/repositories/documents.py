"""Persistence boundary for authorized document association."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_event import AuditEvent
from app.db.models.document import Document
from app.db.models.enums import ActorType, DocumentStatus, RequestStatus
from app.db.models.operations import ExternalManager
from app.db.models.request import ServiceRequest
from app.db.models.whatsapp_message import WhatsAppMessage


@dataclass(frozen=True)
class DocumentTarget:
    request_id: uuid.UUID
    public_id: str
    gestor_id: uuid.UUID


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve_authorized_target(
        self, *, sender_phone: str, context_message_id: str | None, public_id: str | None
    ) -> DocumentTarget | None:
        query = (
            select(ServiceRequest, ExternalManager)
            .join(ExternalManager, ExternalManager.id == ServiceRequest.gestor_id)
            .where(
                ExternalManager.phone_number == sender_phone,
                ExternalManager.is_active,
                ServiceRequest.status.not_in([RequestStatus.COMPLETED, RequestStatus.CANCELLED]),
            )
        )
        if context_message_id:
            query = query.join(
                WhatsAppMessage, WhatsAppMessage.request_id == ServiceRequest.id
            ).where(WhatsAppMessage.provider_message_id == context_message_id)
        elif public_id:
            query = query.where(ServiceRequest.public_id == public_id)
        else:
            return None
        row = (await self._session.execute(query)).first()
        if row is None or row.ServiceRequest.gestor_id is None:
            return None
        request = row.ServiceRequest
        return DocumentTarget(request.id, request.public_id, request.gestor_id)

    async def record(
        self,
        *,
        target: DocumentTarget,
        media_id: str,
        storage_key: str,
        filename: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        expires_at: datetime,
        correlation_id: uuid.UUID,
    ) -> None:
        self._session.add(
            Document(
                request_id=target.request_id,
                provider_media_id=media_id,
                storage_key=storage_key,
                original_filename=filename,
                mime_type=mime_type,
                size_bytes=size_bytes,
                sha256=sha256,
                status=DocumentStatus.QUARANTINED,
                uploaded_by=target.gestor_id,
                expires_at=expires_at,
                next_scan_at=datetime.now(UTC),
            )
        )
        self._session.add(
            AuditEvent(
                request_id=target.request_id,
                actor_id=target.gestor_id,
                actor_type=ActorType.GESTOR,
                event_type="document.quarantined",
                metadata_json={"mime_type": mime_type, "size_bytes": size_bytes},
                correlation_id=correlation_id,
            )
        )
        await self._session.commit()
