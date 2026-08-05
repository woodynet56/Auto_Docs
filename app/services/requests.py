"""Request creation use case; sensitive input never leaves this boundary."""

import re
import uuid
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.repositories.requests import RequestRepository
from app.schemas.webhooks import InboundMessage
from app.services.identifiers import IdentifierProtector
from app.services.whatsapp import MetaWhatsAppClient, WhatsAppDeliveryError, WhatsAppSender

REQUEST_COMMAND = re.compile(r"^\s*SOLICITUD\s*:\s*(\S+)\s*$", re.IGNORECASE)


class InboundRequestProcessor(Protocol):
    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool: ...


class RequestCreationService:
    def __init__(
        self,
        repository: RequestRepository,
        sender: WhatsAppSender,
        sender_phone: str,
        gestor_phone: str,
    ) -> None:
        self._repository = repository
        self._sender = sender
        self._sender_phone = sender_phone
        self._gestor_phone = gestor_phone

    async def create_and_notify(
        self,
        *,
        client_phone: str,
        identifier: str,
        inbound_message_id: str,
        correlation_id: uuid.UUID,
    ) -> str:
        service_request = await self._repository.create(
            client_phone=client_phone,
            gestor_phone=self._gestor_phone,
            identifier=identifier,
            inbound_message_id=inbound_message_id,
            correlation_id=correlation_id,
        )
        notification = (
            f"Nueva solicitud {service_request.public_id}. "
            f"Identificador {service_request.identifier_masked}."
        )
        try:
            provider_id = await self._sender.send_text(self._gestor_phone, notification)
        except WhatsAppDeliveryError:
            await self._repository.record_notification_failure(
                service_request=service_request,
                correlation_id=correlation_id,
            )
            return service_request.public_id
        await self._repository.record_notification(
            service_request=service_request,
            provider_message_id=provider_id,
            sender_phone=self._sender_phone,
            recipient_phone=self._gestor_phone,
            correlation_id=correlation_id,
        )
        return service_request.public_id

    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        if message.message_type != "text" or message.content is None:
            return False
        match = REQUEST_COMMAND.fullmatch(message.content.get_secret_value())
        if match is None:
            return False
        await self.create_and_notify(
            client_phone=f"+{message.sender_phone}",
            identifier=match.group(1),
            inbound_message_id=message.provider_message_id,
            correlation_id=correlation_id,
        )
        return True


class DisabledRequestProcessor:
    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        del message, correlation_id
        return False


def get_request_processor(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InboundRequestProcessor:
    encryption_key = settings.IDENTIFIER_ENCRYPTION_KEY.get_secret_value()
    hash_key = settings.IDENTIFIER_HASH_KEY.get_secret_value()
    access_token = settings.WA_ACCESS_TOKEN.get_secret_value()
    phone_number_id = settings.WA_PHONE_NUMBER_ID or ""
    business_phone = settings.WA_BUSINESS_PHONE_NUMBER or ""
    gestor_phone = settings.GESTOR_PHONE_NUMBER or ""
    if not all(
        (
            encryption_key,
            hash_key,
            access_token,
            phone_number_id,
            business_phone,
            gestor_phone,
        )
    ):
        return DisabledRequestProcessor()
    protector = IdentifierProtector(encryption_key, hash_key)
    repository = RequestRepository(session, protector)
    sender = MetaWhatsAppClient(
        api_version=settings.WA_API_VERSION,
        phone_number_id=phone_number_id,
        access_token=access_token,
        timeout_seconds=settings.META_HTTP_TIMEOUT_SECONDS,
        max_retries=settings.META_MAX_RETRIES,
    )
    return RequestCreationService(
        repository=repository,
        sender=sender,
        sender_phone=business_phone,
        gestor_phone=gestor_phone,
    )
