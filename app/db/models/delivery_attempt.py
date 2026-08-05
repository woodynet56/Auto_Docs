"""Durable, idempotent delivery outbox."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import DeliveryStatus
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeliveryAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "delivery_attempts"
    __table_args__ = (UniqueConstraint("request_id", name="uq_delivery_attempt_request"),)

    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(
            DeliveryStatus,
            name="delivery_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=DeliveryStatus.PENDING,
        server_default=DeliveryStatus.PENDING.value,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[uuid.UUID]
