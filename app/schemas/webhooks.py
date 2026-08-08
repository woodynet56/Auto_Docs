"""Strict, minimal schemas for inbound WhatsApp webhook metadata."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class InboundMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider_message_id: str = Field(min_length=1, max_length=255)
    sender_phone: str = Field(pattern=r"^[1-9][0-9]{7,14}$")
    recipient_phone: str = Field(pattern=r"^[1-9][0-9]{7,14}$")
    message_type: str = Field(min_length=1, max_length=50)
    context_message_id: str | None = Field(default=None, max_length=255)
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content: SecretStr | None = Field(default=None, repr=False)
    media_id: str | None = Field(default=None, max_length=255)
    media_filename: str | None = Field(default=None, max_length=255)
    media_mime_type: str | None = Field(default=None, max_length=127)
    caption: SecretStr | None = Field(default=None, repr=False)


class WebhookResult(BaseModel):
    accepted: int = 0
    duplicates: int = 0
    ignored: int = 0
    requests_created: int = 0
    documents_stored: int = 0
    confirmations_processed: int = 0
