"""Transactional request creation with automatic client and manager resolution."""

import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_event import AuditEvent
from app.db.models.enums import (
    ActorType,
    ClientType,
    ManagerMode,
    MessageProcessingStatus,
    RequestStatus,
)
from app.db.models.operations import Client, ExternalManager
from app.db.models.request import ServiceRequest
from app.db.models.whatsapp_message import WhatsAppMessage
from app.services.folios import generate_folio
from app.services.identifiers import IdentifierProtector, mask_identifier


class GestorUnavailableError(RuntimeError):
    pass


class RequestRepository:
    def __init__(self, session: AsyncSession, protector: IdentifierProtector) -> None:
        self._session = session
        self._protector = protector

    async def _select_manager(
        self, service_type: str, now: datetime
    ) -> tuple[ExternalManager, str] | None:
        managers = list(
            await self._session.scalars(
                select(ExternalManager)
                .where(ExternalManager.is_active)
                .order_by(ExternalManager.priority)
            )
        )
        for manager in managers:
            if (
                manager.mode == ManagerMode.BY_DOCUMENT_TYPE
                and service_type in manager.document_types
            ):
                return manager, "document_type"
        for manager in managers:
            if (
                manager.mode != ManagerMode.BY_SCHEDULE
                or not manager.schedule_start
                or not manager.schedule_end
            ):
                continue
            local_time = now.astimezone(ZoneInfo(manager.timezone)).time().replace(tzinfo=None)
            inside = (
                manager.schedule_start <= local_time < manager.schedule_end
                if manager.schedule_start < manager.schedule_end
                else local_time >= manager.schedule_start or local_time < manager.schedule_end
            )
            if inside:
                return manager, "schedule"
        fallback = next((item for item in managers if item.mode == ManagerMode.FALLBACK), None)
        return (fallback, "fallback") if fallback else None

    async def create(
        self,
        *,
        client_phone: str,
        reference: str | None,
        reference_type: object,
        service_type: str,
        original_message: str,
        inbound_message_id: str,
        correlation_id: uuid.UUID,
    ) -> ServiceRequest:
        client = await self._session.scalar(
            select(Client).where(Client.phone_number == client_phone)
        )
        if client is None:
            client = Client(phone_number=client_phone, client_type=ClientType.RANDOM)
            self._session.add(client)
            await self._session.flush()
        selection = await self._select_manager(service_type, datetime.now(UTC))
        if selection is None:
            raise GestorUnavailableError("No authorized external manager is available")
        manager, reason = selection
        normalized = (reference or "").strip().upper()
        request = ServiceRequest(
            public_id=generate_folio(),
            client_id=client.id,
            gestor_id=manager.id,
            identifier_type=reference_type,
            identifier_encrypted=self._protector.encrypt(normalized) if normalized else None,
            identifier_hash=self._protector.digest(normalized) if normalized else None,
            identifier_masked=mask_identifier(normalized) if normalized else "No proporcionada",
            service_type=service_type,
            original_message=original_message[:2000],
            assignment_reason=reason,
            status=RequestStatus.ASSIGNED,
            assigned_at=datetime.now(UTC),
        )
        self._session.add(request)
        await self._session.flush()
        inbound = await self._session.scalar(
            select(WhatsAppMessage).where(WhatsAppMessage.provider_message_id == inbound_message_id)
        )
        if inbound:
            inbound.request_id = request.id
            inbound.processing_status = MessageProcessingStatus.PROCESSED
            inbound.processed_at = datetime.now(UTC)
        self._session.add(
            AuditEvent(
                request_id=request.id,
                actor_type=ActorType.CLIENT,
                actor_id=None,
                event_type="request.created",
                new_status=RequestStatus.ASSIGNED,
                metadata_json={
                    "client_type": client.client_type.value,
                    "service_type": service_type,
                    "assignment_reason": reason,
                },
                correlation_id=correlation_id,
            )
        )
        await self._session.commit()
        return request

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
                direction="outbound",
                sender_phone=sender_phone,
                recipient_phone=recipient_phone,
                message_type="text",
                processing_status="processed",
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
