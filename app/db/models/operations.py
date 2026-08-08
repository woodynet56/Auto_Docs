"""Operational WhatsApp identities, intentionally separate from portal users."""

from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, CheckConstraint, Enum, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import ClientType, ManagerMode
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.request import ServiceRequest


class Client(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (CheckConstraint("phone_number ~ '^\\+[1-9][0-9]{7,14}$'", name="phone_e164"),)

    phone_number: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    client_type: Mapped[ClientType] = mapped_column(
        Enum(
            ClientType,
            name="client_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ClientType.RANDOM,
        server_default=ClientType.RANDOM.value,
    )
    display_name: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    requests: Mapped[list["ServiceRequest"]] = relationship(back_populates="client")  # noqa: F821


class ExternalManager(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "external_managers"
    __table_args__ = (CheckConstraint("phone_number ~ '^\\+[1-9][0-9]{7,14}$'", name="phone_e164"),)

    name: Mapped[str] = mapped_column(String(160))
    phone_number: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    mode: Mapped[ManagerMode] = mapped_column(
        Enum(
            ManagerMode,
            name="manager_mode",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    document_types: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    schedule_start: Mapped[time | None] = mapped_column(Time)
    schedule_end: Mapped[time | None] = mapped_column(Time)
    timezone: Mapped[str] = mapped_column(
        String(64), default="America/Mexico_City", server_default="America/Mexico_City"
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, server_default="100")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    assigned_requests: Mapped[list["ServiceRequest"]] = relationship(back_populates="gestor")  # noqa: F821
