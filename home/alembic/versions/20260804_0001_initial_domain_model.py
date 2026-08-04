"""Initial domain model with audit and idempotency constraints.

Revision ID: 20260804_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260804_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("client", "gestor", "admin", name="user_role", create_type=False)
identifier_type = postgresql.ENUM("rfc", "curp", name="identifier_type", create_type=False)
request_status = postgresql.ENUM(
    "pending",
    "assigned",
    "processing",
    "awaiting_documents",
    "documents_received",
    "awaiting_confirmation",
    "completed",
    "cancelled",
    "blocked",
    name="request_status",
    create_type=False,
)
document_status = postgresql.ENUM(
    "received",
    "validated",
    "rejected",
    "ready",
    "delivered",
    "delivery_failed",
    "deleted",
    name="document_status",
    create_type=False,
)
message_direction = postgresql.ENUM(
    "inbound", "outbound", name="message_direction", create_type=False
)
message_processing_status = postgresql.ENUM(
    "received",
    "processing",
    "processed",
    "failed",
    "ignored",
    name="message_processing_status",
    create_type=False,
)
actor_type = postgresql.ENUM(
    "client", "gestor", "admin", "system", name="actor_type", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        user_role,
        identifier_type,
        request_status,
        document_status,
        message_direction,
        message_processing_status,
        actor_type,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("phone_number", sa.String(16), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("phone_number ~ '^\\+[1-9][0-9]{7,14}$'", name="ck_users_phone_e164"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("phone_number", name="uq_users_phone_number"),
    )
    op.create_index("ix_users_phone_number", "users", ["phone_number"])
    op.create_table(
        "requests",
        sa.Column("public_id", sa.String(19), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("gestor_id", sa.Uuid()),
        sa.Column("identifier_type", identifier_type, nullable=False),
        sa.Column("identifier_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("identifier_hash", sa.String(64), nullable=False),
        sa.Column("identifier_masked", sa.String(24), nullable=False),
        sa.Column("status", request_status, server_default="pending", nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "public_id ~ '^REQ-[0-9]{8}-[A-Z0-9]{6}$'", name="ck_requests_public_id_format"
        ),
        sa.CheckConstraint("version > 0", name="ck_requests_positive_version"),
        sa.ForeignKeyConstraint(
            ["client_id"], ["users.id"], ondelete="RESTRICT", name="fk_requests_client_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["gestor_id"], ["users.id"], ondelete="SET NULL", name="fk_requests_gestor_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_requests"),
        sa.UniqueConstraint("public_id", name="uq_requests_public_id"),
    )
    op.create_index("ix_requests_identifier_hash", "requests", ["identifier_hash"])
    op.create_index("ix_requests_status_created_at", "requests", ["status", "created_at"])
    op.create_table(
        "documents",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("provider_media_id", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1024)),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("status", document_status, server_default="received", nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("size_bytes > 0", name="ck_documents_positive_size"),
        sa.CheckConstraint("char_length(sha256) = 64", name="ck_documents_sha256_length"),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["requests.id"],
            ondelete="CASCADE",
            name="fk_documents_request_id_requests",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            ondelete="RESTRICT",
            name="fk_documents_uploaded_by_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("provider_media_id", name="uq_documents_provider_media_id"),
        sa.UniqueConstraint("storage_key", name="uq_documents_storage_key"),
        sa.UniqueConstraint("request_id", "sha256", name="uq_documents_request_sha256"),
    )
    op.create_index("ix_documents_request_id", "documents", ["request_id"])
    op.create_table(
        "whatsapp_messages",
        sa.Column("provider_message_id", sa.String(255), nullable=False),
        sa.Column("request_id", sa.Uuid()),
        sa.Column("direction", message_direction, nullable=False),
        sa.Column("sender_phone", sa.String(16), nullable=False),
        sa.Column("recipient_phone", sa.String(16), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("context_message_id", sa.String(255)),
        sa.Column(
            "processing_status",
            message_processing_status,
            server_default="received",
            nullable=False,
        ),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["requests.id"],
            ondelete="SET NULL",
            name="fk_whatsapp_messages_request_id_requests",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_whatsapp_messages"),
        sa.UniqueConstraint("provider_message_id", name="uq_whatsapp_messages_provider_message_id"),
    )
    op.create_index(
        "ix_whatsapp_messages_provider_message_id", "whatsapp_messages", ["provider_message_id"]
    )
    op.create_index("ix_whatsapp_messages_request_id", "whatsapp_messages", ["request_id"])
    op.create_index("ix_whatsapp_messages_context", "whatsapp_messages", ["context_message_id"])
    op.create_table(
        "audit_events",
        sa.Column("request_id", sa.Uuid()),
        sa.Column("actor_type", actor_type, nullable=False),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("previous_status", request_status),
        sa.Column("new_status", request_status),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], ondelete="SET NULL", name="fk_audit_events_actor_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["requests.id"],
            ondelete="SET NULL",
            name="fk_audit_events_request_id_requests",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])
    op.create_index("ix_audit_events_request_created", "audit_events", ["request_id", "created_at"])
    op.execute(
        """
        CREATE FUNCTION reject_audit_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_audit_event_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS reject_audit_event_mutation()")
    for table in ("audit_events", "whatsapp_messages", "documents", "requests", "users"):
        op.drop_table(table)
    bind = op.get_bind()
    for enum_type in (
        actor_type,
        message_processing_status,
        message_direction,
        document_status,
        request_status,
        identifier_type,
        user_role,
    ):
        enum_type.drop(bind, checkfirst=True)
