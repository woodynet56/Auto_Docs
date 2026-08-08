"""Defensive extraction of non-content metadata from Meta webhook payloads."""

from datetime import UTC, datetime
from typing import Any

from app.schemas.webhooks import InboundMessage

SUPPORTED_MESSAGE_TYPES = {"text", "document", "image", "audio", "video", "interactive"}


def parse_whatsapp_messages(payload: Any) -> list[InboundMessage]:
    """Return valid message metadata; never retain message bodies or media content."""
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        return []
    parsed: list[InboundMessage] = []
    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []):
            if not isinstance(change, dict) or change.get("field") != "messages":
                continue
            value = change.get("value", {})
            if not isinstance(value, dict):
                continue
            metadata = value.get("metadata", {})
            recipient = metadata.get("display_phone_number") if isinstance(metadata, dict) else None
            recipient = _digits(recipient)
            if not recipient:
                continue
            for message in value.get("messages", []):
                item = _parse_message(message, recipient)
                if item is not None:
                    parsed.append(item)
    return parsed


def _parse_message(message: Any, recipient: str) -> InboundMessage | None:
    if not isinstance(message, dict) or message.get("type") not in SUPPORTED_MESSAGE_TYPES:
        return None
    timestamp = message.get("timestamp")
    if not isinstance(timestamp, (str, int)):
        return None
    try:
        received_at = datetime.fromtimestamp(int(timestamp), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None
    context = message.get("context", {})
    context_id = context.get("id") if isinstance(context, dict) else None
    text_content = message.get("text", {})
    content = text_content.get("body") if isinstance(text_content, dict) else None
    media = message.get(message.get("type"), {})
    media = media if isinstance(media, dict) else {}
    try:
        return InboundMessage(
            provider_message_id=message.get("id"),
            sender_phone=_digits(message.get("from")),
            recipient_phone=recipient,
            message_type=message.get("type"),
            context_message_id=context_id,
            received_at=received_at,
            content=content if isinstance(content, str) else None,
            media_id=media.get("id") if isinstance(media.get("id"), str) else None,
            media_filename=(
                media.get("filename") if isinstance(media.get("filename"), str) else None
            ),
            media_mime_type=(
                media.get("mime_type") if isinstance(media.get("mime_type"), str) else None
            ),
            caption=media.get("caption") if isinstance(media.get("caption"), str) else None,
        )
    except ValueError:
        return None


def _digits(value: Any) -> str:
    return value if isinstance(value, str) and value.isascii() and value.isdigit() else ""
