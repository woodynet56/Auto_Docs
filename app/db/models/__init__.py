"""Database model registry imported by Alembic."""

from app.db.models.audit_event import AuditEvent
from app.db.models.delivery_attempt import DeliveryAttempt
from app.db.models.document import Document
from app.db.models.portal_access import DocumentDownloadEvent, PortalAccessGrant
from app.db.models.request import ServiceRequest
from app.db.models.user import User
from app.db.models.whatsapp_message import WhatsAppMessage

__all__ = [
    "AuditEvent",
    "DeliveryAttempt",
    "Document",
    "DocumentDownloadEvent",
    "PortalAccessGrant",
    "ServiceRequest",
    "User",
    "WhatsAppMessage",
]
