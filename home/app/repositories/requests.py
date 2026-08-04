"""Transactional persistence for service-request creation and notification ledger."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_event import AuditEvent
from app.db.models.enums import (
    ActorType,
    MessageDirection,
    MessageProcessingStatus,
    RequestStatus,
    UserRole,
)
from app.db.models.request import ServiceRequest
from app.db.models.user import User
from app.db.models.whatsapp_message import WhatsAppMessage
from app.services.folios import generate_folio
from app.services.identifiers import IdentifierProtector, identify_and_validate, mask_identifier


class GestorUnavailableError(RuntimeError):
    pass


class RequestRepository:
    def __init__(self, session: AsyncSession, protector: IdentifierProtector) -> None:
        self._session = session
        self._protector = protector

    async def create(
        self,
        *,
        client_phone: str,
        gestor_phone: str,
        identifier: str,
        inbound_message_id: str,
        correlation_id: uuid.UUID,
    ) -> ServiceRequest:
        identifier_type, normalized = identify_and_validate(identifier)
        gestor = await self._session.scalar(
            select(User).where(
                User.phone_number == gestor_phone,
                User.role == UserRole.GESTOR,
                User.is_active.is_(True),
            )
        )
        if gestor is None:
            raise GestorUnavailableError("No authorized gestor is available")
        client = await self._session.scalar(select(User).where(User.phone_number == client_phone))
        if client is None:
            client = User(phone_number=client_phone, role=UserRole.CLIENT)
            self._session.add(client)
            await self._session.flush()
        service_request = ServiceRequest(
            public_id=generate_folio(),
            client_id=client.id,
            gestor_id=gestor.id,
            identifier_type=identifier_type,
            identifier_encrypted=self._protector.encrypt(normalized),
            identifier_hash=self._protector.digest(normalized),
            identifier_masked=mask_identifier(normalized),
            status=RequestStatus.ASSIGNED,
            assigned_at=datetime.now(UTC),
        )
        self._session.add(service_request)
        await self._session.flush()
        inbound_message = await self._session.scalar(
            select(WhatsAppMessage).where(WhatsAppMessage.provider_message_id == inbound_message_id)
        )
        if inbound_message is not None:
            inbound_message.request_id = service_request.id
            inbound_message.processing_status = MessageProcessingStatus.PROCESSED
            inbound_message.processed_at = datetime.now(UTC)
        self._session.add(
            AuditEvent(
                request_id=service_request.id,
                actor_type=ActorType.CLIENT,
                actor_id=client.id,
                event_type="request.created",
                previous_status=None,
                new_status=RequestStatus.ASSIGNED,
                metadata_json={"identifier_type": identifier_type.value},
                correlation_id=correlation_id,
            )
        )
        await self._session.commit()
        return service_request

    async def record_notification(
        self,
        *,
        service_request: ServiceRequest,
        provider_message_id: str,
        sender_phone: str,
        recipient_phone: str,
        correlation_id: uuid.UUID,
    ) -> None:
        self._session.add(
            WhatsAppMessage(
                provider_message_id=provider_message_id,
                request_id=service_request.id,
                direction=MessageDirection.OUTBOUND,
                sender_phone=sender_phone,
                recipient_phone=recipient_phone,
                message_type="text",
                processing_status=MessageProcessingStatus.PROCESSED,
                received_at=datetime.now(UTC),
                processed_at=datetime.now(UTC),
            )
        )
        self._session.add(
            AuditEvent(
                request_id=service_request.id,
                actor_type=ActorType.SYSTEM,
                event_type="request.gestor_notified",
                new_status=service_request.status,
                metadata_json={},
                correlation_id=correlation_id,
            )
        )
        await self._session.commit()

    async def record_notification_failure(
        self, *, service_request: ServiceRequest, correlation_id: uuid.UUID
    ) -> None:
        self._session.add(
            AuditEvent(
                request_id=service_request.id,
                actor_type=ActorType.SYSTEM,
                event_type="request.gestor_notification_failed",
                new_status=service_request.status,
                metadata_json={"recoverable": True},
                correlation_id=correlation_id,
            )
        )
        await self._session.commit()
