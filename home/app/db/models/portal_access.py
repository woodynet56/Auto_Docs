"""Revocable, hashed portal credentials and individual download records."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import PortalGrantStatus
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PortalAccessGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "portal_access_grants"

    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), unique=True, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[PortalGrantStatus] = mapped_column(
        Enum(
            PortalGrantStatus,
            name="portal_grant_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=PortalGrantStatus.ACTIVE,
        server_default=PortalGrantStatus.ACTIVE.value,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_hash: Mapped[str] = mapped_column(String(64))
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    otp_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    otp_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentDownloadEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_download_events"

    grant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portal_access_grants.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", index=True
    )
    outcome: Mapped[str] = mapped_column(String(32))
