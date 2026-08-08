"""Deliver the first clean document to the request owner exactly once."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.audit_event import AuditEvent
from app.db.models.delivery_attempt import DeliveryAttempt
from app.db.models.document import Document
from app.db.models.enums import ActorType, DeliveryStatus, DocumentStatus, RequestStatus
from app.db.models.request import ServiceRequest
from app.services.r2 import R2StorageClient
from app.services.whatsapp import WhatsAppDeliveryError, WhatsAppSender


class AutomaticDeliveryService:
    def __init__(
        self,
        session: AsyncSession,
        storage: R2StorageClient,
        sender: WhatsAppSender,
        ttl_seconds: int = 600,
    ) -> None:
        self.session, self.storage, self.sender, self.ttl = session, storage, sender, ttl_seconds

    async def process_due(self, limit: int = 20) -> int:
        documents = list(
            await self.session.scalars(
                select(Document)
                .join(ServiceRequest)
                .where(
                    Document.status == DocumentStatus.CLEAN,
                    ServiceRequest.status.not_in(
                        [RequestStatus.COMPLETED, RequestStatus.CANCELLED]
                    ),
                )
                .order_by(Document.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        delivered = 0
        for document in documents:
            request = await self.session.scalar(
                select(ServiceRequest)
                .options(selectinload(ServiceRequest.client))
                .where(ServiceRequest.id == document.request_id)
                .with_for_update()
            )
            if request is None or request.status in {
                RequestStatus.COMPLETED,
                RequestStatus.CANCELLED,
            }:
                document.status = DocumentStatus.REJECTED
                continue
            attempt = await self.session.scalar(
                select(DeliveryAttempt).where(DeliveryAttempt.request_id == request.id)
            )
            if attempt and attempt.status == DeliveryStatus.SENT:
                document.status = DocumentStatus.REJECTED
                continue
            if attempt is None:
                attempt = DeliveryAttempt(
                    request_id=request.id,
                    correlation_id=uuid.uuid4(),
                    attempt_count=0,
                    status=DeliveryStatus.PENDING,
                )
                self.session.add(attempt)
            attempt.attempt_count += 1
            try:
                provider_id = await self.sender.send_document(
                    request.client.phone_number,
                    self.storage.presign_get(document.storage_key or "", self.ttl),
                    document.original_filename,
                    f"Documento correspondiente a {request.public_id}",
                )
                await self.sender.send_text(
                    request.client.phone_number,
                    f"Tu solicitud {request.public_id} fue completada correctamente.",
                )
            except WhatsAppDeliveryError:
                attempt.status = DeliveryStatus.PENDING
                attempt.next_attempt_at = datetime.now(UTC) + timedelta(minutes=2)
                await self.session.commit()
                continue
            attempt.status, attempt.provider_message_id, attempt.next_attempt_at = (
                DeliveryStatus.SENT,
                provider_id,
                None,
            )
            request.status, request.completed_at = RequestStatus.COMPLETED, datetime.now(UTC)
            document.status, document.delivered_at, document.delivery_message_id = (
                DocumentStatus.DELIVERED,
                request.completed_at,
                provider_id,
            )
            self.session.add(
                AuditEvent(
                    request_id=request.id,
                    actor_type=ActorType.SYSTEM,
                    event_type="delivery.completed_automatic",
                    new_status=RequestStatus.COMPLETED,
                    metadata_json={"document_id": str(document.id)},
                    correlation_id=attempt.correlation_id,
                )
            )
            await self.session.commit()
            delivered += 1
        return delivered
