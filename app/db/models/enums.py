"""Closed vocabularies persisted by the domain model."""

from enum import StrEnum


class UserRole(StrEnum):
    CLIENT = "client"
    GESTOR = "gestor"
    ADMIN = "admin"


class ClientType(StrEnum):
    FIXED = "fixed"
    RANDOM = "random"


class ManagerMode(StrEnum):
    BY_DOCUMENT_TYPE = "by_document_type"
    BY_SCHEDULE = "by_schedule"
    FALLBACK = "fallback"


class IdentifierType(StrEnum):
    RFC = "rfc"
    CURP = "curp"
    OTHER = "other"
    NOT_PROVIDED = "not_provided"


class RequestStatus(StrEnum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    AWAITING_DOCUMENTS = "awaiting_documents"
    DOCUMENTS_RECEIVED = "documents_received"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class DocumentStatus(StrEnum):
    RECEIVED = "received"
    QUARANTINED = "quarantined"
    CLEAN = "clean"
    INFECTED = "infected"
    SCAN_FAILED = "scan_failed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    READY = "ready"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"
    DELETED = "deleted"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageProcessingStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


class ActorType(StrEnum):
    CLIENT = "client"
    GESTOR = "gestor"
    ADMIN = "admin"
    SYSTEM = "system"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"


class PortalGrantStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
