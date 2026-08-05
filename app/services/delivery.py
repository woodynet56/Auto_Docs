"""Explicit gestor confirmation and idempotent client delivery."""

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.db.models.audit_event import AuditEvent
from app.db.models.delivery_attempt import DeliveryAttempt
from app.db.models.document import Document
from app.db.models.enums import ActorType, DeliveryStatus, DocumentStatus, RequestStatus, UserRole
from app.db.models.request import ServiceRequest
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.webhooks import InboundMessage
from app.services.portal import issue_grant
from app.services.r2 import R2StorageClient
from app.services.request_states import ensure_transition_allowed
from app.services.whatsapp import MetaWhatsAppClient, WhatsAppDeliveryError, WhatsAppSender

CONFIRM_PATTERN = re.compile(r"^CONFIRMAR\s+(REQ-[0-9]{8}-[A-Z0-9]{6})$", re.IGNORECASE)


class DeliveryProcessor(Protocol):
    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool: ...


class DisabledDeliveryProcessor:
    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        return False


class DeliveryService:
    def __init__(
        self,
        session: AsyncSession,
        storage: R2StorageClient,
        sender: WhatsAppSender,
        business_phone: str,
        link_ttl_seconds: int = 600,
        maximum_attempts: int = 3,
        public_base_url: str = "http://localhost:8000",
        portal_ttl_minutes: int = 30,
    ) -> None:
        self._session = session
        self._storage = storage
        self._sender = sender
        self._business_phone = business_phone
        self._ttl = link_ttl_seconds
        self._maximum_attempts = maximum_attempts
        self._public_base_url = public_base_url.rstrip("/")
        self._portal_ttl_minutes = portal_ttl_minutes

    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        content = message.content.get_secret_value().strip() if message.content else ""
        match = CONFIRM_PATTERN.fullmatch(content)
        if not match:
            return False
        request = await self._authorized_request(message.sender_phone, match.group(1).upper())
        if request is None:
            return True
        documents = list(
            await self._session.scalars(
                select(Document).where(
                    Document.request_id == request.id,
                    Document.status.in_([DocumentStatus.CLEAN, DocumentStatus.READY]),
                    Document.expires_at > datetime.now(UTC),
                    Document.storage_key.is_not(None),
                )
            )
        )
        if not documents:
            await self._audit(request, "delivery.rejected_no_documents", correlation_id)
            return True
        ensure_transition_allowed(request.status, RequestStatus.AWAITING_CONFIRMATION)
        request.status = RequestStatus.AWAITING_CONFIRMATION
        for document in documents:
            document.status = DocumentStatus.READY
        attempt = await self._session.scalar(
            select(DeliveryAttempt).where(DeliveryAttempt.request_id == request.id)
        )
        if attempt is None:
            attempt = DeliveryAttempt(
                request_id=request.id,
                correlation_id=correlation_id,
                attempt_count=0,
                status=DeliveryStatus.PENDING,
            )
            self._session.add(attempt)
        if attempt.status == DeliveryStatus.SENT:
            return True
        await self._session.commit()
        await self._deliver(request, documents, attempt, correlation_id)
        return True

    async def retry_due(self, limit: int = 20) -> int:
        """Retry due outbox rows; suitable for a single scheduled worker."""
        now = datetime.now(UTC)
        attempts = list(
            await self._session.scalars(
                select(DeliveryAttempt)
                .where(
                    DeliveryAttempt.status == DeliveryStatus.PENDING,
                    DeliveryAttempt.next_attempt_at <= now,
                    DeliveryAttempt.attempt_count < self._maximum_attempts,
                )
                .order_by(DeliveryAttempt.next_attempt_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        processed = 0
        for attempt in attempts:
            request = await self._session.scalar(
                select(ServiceRequest)
                .options(selectinload(ServiceRequest.client))
                .where(ServiceRequest.id == attempt.request_id)
            )
            if request is None or request.status != RequestStatus.AWAITING_CONFIRMATION:
                attempt.status = DeliveryStatus.FAILED
                attempt.last_error_code = "request_not_deliverable"
                await self._session.commit()
                continue
            documents = list(
                await self._session.scalars(
                    select(Document).where(
                        Document.request_id == request.id,
                        Document.status == DocumentStatus.READY,
                        Document.expires_at > now,
                        Document.storage_key.is_not(None),
                    )
                )
            )
            if not documents:
                attempt.status = DeliveryStatus.FAILED
                attempt.last_error_code = "documents_unavailable"
                await self._session.commit()
                continue
            await self._deliver(request, documents, attempt, attempt.correlation_id)
            processed += 1
        return processed

    async def _authorized_request(self, sender: str, public_id: str) -> ServiceRequest | None:
        result = await self._session.scalar(
            select(ServiceRequest)
            .options(selectinload(ServiceRequest.client))
            .join(User, User.id == ServiceRequest.gestor_id)
            .where(
                ServiceRequest.public_id == public_id,
                ServiceRequest.status == RequestStatus.DOCUMENTS_RECEIVED,
                User.phone_number == sender,
                User.role == UserRole.GESTOR,
                User.is_active.is_(True),
            )
        )
        return result

    async def _deliver(
        self,
        request: ServiceRequest,
        documents: list[Document],
        attempt: DeliveryAttempt,
        correlation_id: uuid.UUID,
    ) -> None:
        attempt.status = DeliveryStatus.PROCESSING
        attempt.attempt_count += 1
        _, portal_token, otp = await issue_grant(
            self._session, request.id, self._portal_ttl_minutes
        )
        portal_url = f"{self._public_base_url}/portal/acceso?token={portal_token}"
        body = "\n".join(
            [
                f"Gestoría Reaver: documentos disponibles para {request.public_id}.",
                f"Acceso personal válido por {self._portal_ttl_minutes} minutos:",
                portal_url,
            ]
        )
        try:
            provider_id = await self._sender.send_text(request.client.phone_number, body)
            await self._sender.send_text(
                request.client.phone_number,
                f"Código de verificación Gestoría Reaver: {otp}. No lo compartas.",
            )
        except WhatsAppDeliveryError:
            final = attempt.attempt_count >= self._maximum_attempts
            attempt.status = DeliveryStatus.FAILED if final else DeliveryStatus.PENDING
            attempt.next_attempt_at = None if final else datetime.now(UTC) + timedelta(minutes=2)
            attempt.last_error_code = "meta_delivery_failed"
            event_type = "delivery.failed" if final else "delivery.retry_scheduled"
            await self._audit(request, event_type, correlation_id)
            return
        attempt.status = DeliveryStatus.SENT
        attempt.provider_message_id = provider_id
        attempt.next_attempt_at = None
        request.status = RequestStatus.COMPLETED
        request.completed_at = datetime.now(UTC)
        for document in documents:
            document.status = DocumentStatus.DELIVERED
            document.delivered_at = request.completed_at
            document.delivery_message_id = provider_id
        await self._audit(request, "delivery.completed", correlation_id)

    async def _audit(
        self, request: ServiceRequest, event_type: str, correlation_id: uuid.UUID
    ) -> None:
        self._session.add(
            AuditEvent(
                request_id=request.id,
                actor_type=ActorType.SYSTEM,
                event_type=event_type,
                new_status=request.status,
                metadata_json={},
                correlation_id=correlation_id,
            )
        )
        await self._session.commit()


def get_delivery_processor(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DeliveryProcessor:
    endpoint = settings.R2_ENDPOINT_URL or ""
    bucket = settings.R2_BUCKET_NAME or ""
    access_key = settings.R2_ACCESS_KEY_ID.get_secret_value()
    secret_key = settings.R2_SECRET_ACCESS_KEY.get_secret_value()
    business_phone = settings.WA_BUSINESS_PHONE_NUMBER or ""
    phone_id = settings.WA_PHONE_NUMBER_ID or ""
    token = settings.WA_ACCESS_TOKEN.get_secret_value()
    if not all((endpoint, bucket, access_key, secret_key, business_phone, phone_id, token)):
        return DisabledDeliveryProcessor()
    return DeliveryService(
        session=session,
        storage=R2StorageClient(endpoint, bucket, access_key, secret_key),
        sender=MetaWhatsAppClient(
            api_version=settings.WA_API_VERSION,
            phone_number_id=phone_id,
            access_token=token,
            timeout_seconds=settings.META_HTTP_TIMEOUT_SECONDS,
            max_retries=settings.META_MAX_RETRIES,
        ),
        business_phone=business_phone,
        link_ttl_seconds=settings.DELIVERY_LINK_TTL_SECONDS,
        maximum_attempts=settings.DELIVERY_MAX_ATTEMPTS,
        public_base_url=settings.PUBLIC_BASE_URL,
        portal_ttl_minutes=settings.PORTAL_SESSION_TTL_MINUTES,
    )
