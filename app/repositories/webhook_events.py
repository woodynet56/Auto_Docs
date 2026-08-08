"""Persistence boundary for idempotent inbound webhook events."""

import uuid
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_event import AuditEvent
from app.db.models.enums import ActorType, MessageDirection, MessageProcessingStatus
from app.db.models.whatsapp_message import WhatsAppMessage
from app.db.session import get_session
from app.schemas.webhooks import InboundMessage


class WebhookEventRepository(Protocol):
    async def add_if_new(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool: ...


class SqlAlchemyWebhookEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_new(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        try:
            async with self._session.begin_nested():
                self._session.add(
                    WhatsAppMessage(
                        provider_message_id=message.provider_message_id,
                        direction=MessageDirection.INBOUND,
                        sender_phone=message.sender_phone,
                        recipient_phone=message.recipient_phone,
                        message_type=message.message_type,
                        context_message_id=message.context_message_id,
                        processing_status=MessageProcessingStatus.RECEIVED,
                        received_at=message.received_at,
                    )
                )
                await self._session.flush()
                self._session.add(
                    AuditEvent(
                        actor_type=ActorType.SYSTEM,
                        event_type="webhook.message_received",
                        metadata_json={"message_type": message.message_type},
                        correlation_id=correlation_id,
                    )
                )
            await self._session.commit()
            return True
        except IntegrityError:
            await self._session.rollback()
            return False


def get_webhook_event_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WebhookEventRepository:
    return SqlAlchemyWebhookEventRepository(session)
