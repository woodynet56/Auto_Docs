import uuid

import pytest
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.db.models import AuditEvent, ServiceRequest, User, WhatsAppMessage
from app.db.models.audit_event import prevent_audit_mutation
from app.db.models.enums import ActorType, IdentifierType, MessageDirection, UserRole


def test_metadata_contains_the_five_domain_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "requests",
        "documents",
        "whatsapp_messages",
        "audit_events",
        "delivery_attempts",
        "portal_access_grants",
        "document_download_events",
    }


def test_domain_models_compile_for_postgresql() -> None:
    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]
    for table in Base.metadata.sorted_tables:
        assert str(table.compile(dialect=dialect)) == ""
        for index in table.indexes:
            assert index.name


def test_models_use_safe_defaults_and_relationship_ids() -> None:
    client = User(phone_number="+525500000001", role=UserRole.CLIENT)
    request = ServiceRequest(
        public_id="REQ-20260804-A1B2C3",
        client=client,
        identifier_type=IdentifierType.RFC,
        identifier_encrypted=b"ciphertext",
        identifier_hash="a" * 64,
        identifier_masked="GODE******GR8",
    )
    message = WhatsAppMessage(
        provider_message_id="wamid.synthetic-1",
        request=request,
        direction=MessageDirection.INBOUND,
        sender_phone=client.phone_number,
        recipient_phone="+525500000099",
        message_type="text",
    )
    assert request.public_id.startswith("REQ-")
    assert message.request is request


def test_audit_events_reject_mutation() -> None:
    event = AuditEvent(
        actor_type=ActorType.SYSTEM,
        event_type="request.created",
        correlation_id=uuid.uuid4(),
        metadata_json={},
    )
    with pytest.raises(ValueError, match="append-only"):
        prevent_audit_mutation(None, None, event)
