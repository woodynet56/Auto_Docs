"""Inbound/outbound message ledger and webhook idempotency boundary."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import MessageDirection, MessageProcessingStatus
from app.db.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.request import ServiceRequest


class WhatsAppMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "whatsapp_messages"
    __table_args__ = (Index("ix_whatsapp_messages_context", "context_message_id"),)

    provider_message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(
            MessageDirection,
            name="message_direction",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    sender_phone: Mapped[str] = mapped_column(String(16))
    recipient_phone: Mapped[str] = mapped_column(String(16))
    message_type: Mapped[str] = mapped_column(String(50))
    context_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processing_status: Mapped[MessageProcessingStatus] = mapped_column(
        Enum(
            MessageProcessingStatus,
            name="message_processing_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=MessageProcessingStatus.RECEIVED,
        server_default=MessageProcessingStatus.RECEIVED.value,
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    request: Mapped["ServiceRequest | None"] = relationship(back_populates="messages")  # noqa: F821
