"""Document service request aggregate root."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import IdentifierType, RequestStatus
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.audit_event import AuditEvent
    from app.db.models.document import Document
    from app.db.models.user import User
    from app.db.models.whatsapp_message import WhatsAppMessage


class ServiceRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint("public_id ~ '^REQ-[0-9]{8}-[A-Z0-9]{6}$'", name="public_id_format"),
        CheckConstraint("version > 0", name="positive_version"),
        Index("ix_requests_status_created_at", "status", "created_at"),
    )

    public_id: Mapped[str] = mapped_column(String(19), unique=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    gestor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    identifier_type: Mapped[IdentifierType] = mapped_column(
        Enum(
            IdentifierType,
            name="identifier_type",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    identifier_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    identifier_hash: Mapped[str] = mapped_column(String(64), index=True)
    identifier_masked: Mapped[str] = mapped_column(String(24))
    status: Mapped[RequestStatus] = mapped_column(
        Enum(
            RequestStatus,
            name="request_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=RequestStatus.PENDING,
        server_default=RequestStatus.PENDING.value,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    client: Mapped["User"] = relationship(  # noqa: F821
        back_populates="client_requests", foreign_keys=[client_id]
    )
    gestor: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="assigned_requests", foreign_keys=[gestor_id]
    )
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        back_populates="request", cascade="all, delete-orphan"
    )
    messages: Mapped[list["WhatsAppMessage"]] = relationship(  # noqa: F821
        back_populates="request"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(  # noqa: F821
        back_populates="request"
    )

    __mapper_args__ = {"version_id_col": version}
