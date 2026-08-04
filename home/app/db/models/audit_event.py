"""Append-only business audit trail with intentionally minimal metadata."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, event
from sqlalchemy.orm import Mapped, Mapper, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import ActorType, RequestStatus
from app.db.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.request import ServiceRequest


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_request_created", "request_id", "created_at"),)

    request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("requests.id", ondelete="SET NULL"), nullable=True
    )
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(
            ActorType, name="actor_type", values_callable=lambda enum: [item.value for item in enum]
        )
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(100))
    previous_status: Mapped[RequestStatus | None] = mapped_column(
        Enum(
            RequestStatus,
            name="request_status",
            values_callable=lambda enum: [item.value for item in enum],
            create_type=False,
        ),
        nullable=True,
    )
    new_status: Mapped[RequestStatus | None] = mapped_column(
        Enum(
            RequestStatus,
            name="request_status",
            values_callable=lambda enum: [item.value for item in enum],
            create_type=False,
        ),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    correlation_id: Mapped[uuid.UUID] = mapped_column(index=True)

    request: Mapped["ServiceRequest | None"] = relationship(back_populates="audit_events")  # noqa: F821


@event.listens_for(AuditEvent, "before_update")
@event.listens_for(AuditEvent, "before_delete")
def prevent_audit_mutation(mapper: Mapper[Any], connection: Any, target: AuditEvent) -> None:
    del mapper, connection, target
    raise ValueError("audit events are append-only")
