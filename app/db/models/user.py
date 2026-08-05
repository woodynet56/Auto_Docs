"""Platform identities; phone numbers are normalized before persistence."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import UserRole
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.request import ServiceRequest


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("phone_number ~ '^\\+[1-9][0-9]{7,14}$'", name="phone_e164"),)

    phone_number: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda enum: [item.value for item in enum])
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    client_requests: Mapped[list["ServiceRequest"]] = relationship(  # noqa: F821
        back_populates="client", foreign_keys="ServiceRequest.client_id"
    )
    assigned_requests: Mapped[list["ServiceRequest"]] = relationship(  # noqa: F821
        back_populates="gestor", foreign_keys="ServiceRequest.gestor_id"
    )
