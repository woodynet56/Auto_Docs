"""Authenticated Meta WhatsApp webhook endpoints."""

import hmac
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.security import verify_meta_signature
from app.repositories.webhook_events import WebhookEventRepository, get_webhook_event_repository
from app.schemas.webhooks import WebhookResult
from app.services.delivery import DeliveryProcessor, get_delivery_processor
from app.services.documents import DocumentProcessor, get_document_processor
from app.services.requests import InboundRequestProcessor, get_request_processor
from app.services.webhook_parser import parse_whatsapp_messages

router = APIRouter(prefix="/webhooks/meta", tags=["webhooks"])


@router.get("/whatsapp", response_class=Response)
async def verify_webhook(
    settings: Annotated[Settings, Depends(get_settings)],
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    expected = settings.WA_VERIFY_TOKEN.get_secret_value()
    valid_token = bool(expected) and token is not None and hmac.compare_digest(token, expected)
    if mode != "subscribe" or not valid_token or challenge is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")
    return Response(content=challenge, media_type="text/plain")


@router.post("/whatsapp", response_model=WebhookResult)
async def receive_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[WebhookEventRepository, Depends(get_webhook_event_repository)],
    processor: Annotated[InboundRequestProcessor, Depends(get_request_processor)],
    document_processor: Annotated[DocumentProcessor, Depends(get_document_processor)],
    delivery_processor: Annotated[DeliveryProcessor, Depends(get_delivery_processor)],
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
) -> WebhookResult:
    content_length = request.headers.get("content-length")
    if content_length and (
        not content_length.isdigit() or int(content_length) > settings.WEBHOOK_MAX_BODY_BYTES
    ):
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Payload too large"
        )
    body = await request.body()
    if len(body) > settings.WEBHOOK_MAX_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Payload too large"
        )
    if not verify_meta_signature(body, signature, settings.WA_APP_SECRET.get_secret_value()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON"
        ) from error
    messages = parse_whatsapp_messages(payload)
    result = WebhookResult(ignored=0 if messages else 1)
    for message in messages:
        correlation_id = uuid.uuid4()
        if await repository.add_if_new(message, correlation_id):
            result.accepted += 1
            if await delivery_processor.process(message, correlation_id):
                result.confirmations_processed += 1
            elif await document_processor.process(message, correlation_id):
                result.documents_stored += 1
            elif await processor.process(message, correlation_id):
                result.requests_created += 1
        else:
            result.duplicates += 1
    return result
