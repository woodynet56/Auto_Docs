"""Natural-language WhatsApp request intake."""

import re
import uuid
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models.enums import IdentifierType
from app.db.session import get_session
from app.repositories.requests import GestorUnavailableError, RequestRepository
from app.schemas.webhooks import InboundMessage
from app.services.identifiers import IdentifierProtector
from app.services.whatsapp import MetaWhatsAppClient, TextSender, WhatsAppDeliveryError

REFERENCE = re.compile(
    r"\b(?=[A-Z&Ñ0-9]{9,18}\b)(?=[A-Z&Ñ0-9]*\d)[A-Z&Ñ]{3,4}[A-Z0-9]{5,14}\b", re.IGNORECASE
)
SERVICES = {
    "acta_matrimonio": ("matrimonio", "cata matrimonio"),
    "acta_nacimiento": ("acta", "nacimiento"),
    "antecedentes": ("antecedente", "carta de antecedente"),
    "constancia_fiscal": ("constancia", "situacion fiscal", "situación fiscal", "constanci"),
    "curp": ("curp",),
}


@dataclass(frozen=True)
class ParsedIntent:
    service_type: str
    reference: str | None
    reference_type: IdentifierType


def parse_intent(text: str) -> ParsedIntent:
    folded = text.casefold()
    service = next(
        (name for name, words in SERVICES.items() if any(word in folded for word in words)), "other"
    )
    match = REFERENCE.search(text.upper())
    reference = match.group(0) if match else None
    if not reference:
        kind = IdentifierType.NOT_PROVIDED
    elif service == "curp" or len(reference) == 18:
        kind = IdentifierType.CURP
    elif service == "constancia_fiscal":
        kind = IdentifierType.RFC
    else:
        kind = IdentifierType.OTHER
    return ParsedIntent(service, reference, kind)


class InboundRequestProcessor(Protocol):
    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool: ...


class RequestCreationService:
    def __init__(
        self, repository: RequestRepository, sender: TextSender, sender_phone: str
    ) -> None:
        self._repository, self._sender, self._sender_phone = repository, sender, sender_phone

    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        if message.message_type != "text" or not message.content:
            return False
        original = message.content.get_secret_value().strip()
        if not original:
            return False
        intent = parse_intent(original)
        try:
            request = await self._repository.create(
                client_phone=f"+{message.sender_phone}",
                reference=intent.reference,
                reference_type=intent.reference_type,
                service_type=intent.service_type,
                original_message=original,
                inbound_message_id=message.provider_message_id,
                correlation_id=correlation_id,
            )
        except GestorUnavailableError:
            return True
        manager = request.gestor
        if manager is None:
            await self._repository.record_notification_failure(
                service_request=request, correlation_id=correlation_id
            )
            return True
        body = "\n".join(
            [
                f"Nueva solicitud: {request.public_id}",
                f"Trámite: {request.service_type}",
                f"Referencia: {request.identifier_masked}",
                f"Mensaje original: {request.original_message}",
                f"Responda citando este mensaje o escribiendo {request.public_id} "
                "y adjunte el archivo.",
            ]
        )
        try:
            provider_id = await self._sender.send_text(manager.phone_number, body)
        except WhatsAppDeliveryError:
            await self._repository.record_notification_failure(
                service_request=request, correlation_id=correlation_id
            )
            return True
        await self._repository.record_notification(
            service_request=request,
            provider_message_id=provider_id,
            sender_phone=self._sender_phone,
            recipient_phone=manager.phone_number,
            correlation_id=correlation_id,
        )
        await self._sender.send_text(
            f"+{message.sender_phone}", f"Solicitud recibida. Tu folio es {request.public_id}."
        )
        return True


class DisabledRequestProcessor:
    async def process(self, message: InboundMessage, correlation_id: uuid.UUID) -> bool:
        return False


def get_request_processor(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InboundRequestProcessor:
    required = (
        settings.IDENTIFIER_ENCRYPTION_KEY.get_secret_value(),
        settings.IDENTIFIER_HASH_KEY.get_secret_value(),
        settings.WA_ACCESS_TOKEN.get_secret_value(),
        settings.WA_PHONE_NUMBER_ID,
        settings.WA_BUSINESS_PHONE_NUMBER,
    )
    if not all(required):
        return DisabledRequestProcessor()
    return RequestCreationService(
        RequestRepository(session, IdentifierProtector(required[0], required[1])),
        MetaWhatsAppClient(
            api_version=settings.WA_API_VERSION,
            phone_number_id=required[3] or "",
            access_token=required[2],
            timeout_seconds=settings.META_HTTP_TIMEOUT_SECONDS,
            max_retries=settings.META_MAX_RETRIES,
        ),
        required[4] or "",
    )
