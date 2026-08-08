"""Metadata for privately stored documents; binary data is never stored here."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import DocumentStatus
from app.db.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.request import ServiceRequest


class Document(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("request_id", "sha256", name="uq_documents_request_sha256"),
        CheckConstraint("size_bytes > 0", name="positive_size"),
        CheckConstraint("char_length(sha256) = 64", name="sha256_length"),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), index=True
    )
    provider_media_id: Mapped[str] = mapped_column(String(255), unique=True)
    storage_key: Mapped[str | None] = mapped_column(String(1024), unique=True, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=DocumentStatus.RECEIVED,
        server_default=DocumentStatus.RECEIVED.value,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_managers.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_message_id: Mapped[str | None] = mapped_column(String(255))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    scan_attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    scan_engine: Mapped[str | None] = mapped_column(String(64))
    scan_signature: Mapped[str | None] = mapped_column(String(255))
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    next_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    request: Mapped["ServiceRequest"] = relationship(back_populates="documents")  # noqa: F821
