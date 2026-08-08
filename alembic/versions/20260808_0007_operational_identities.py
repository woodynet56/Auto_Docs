"""Separate clients/managers and support flexible request intake.

Revision ID: 20260808_0007
Revises: 20260804_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260808_0007"
down_revision: str | None = "20260804_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    client_type = postgresql.ENUM("fixed", "random", name="client_type")
    manager_mode = postgresql.ENUM(
        "by_document_type", "by_schedule", "fallback", name="manager_mode"
    )
    client_type.create(bind, checkfirst=True)
    manager_mode.create(bind, checkfirst=True)
    op.execute("ALTER TYPE identifier_type ADD VALUE IF NOT EXISTS 'other'")
    op.execute("ALTER TYPE identifier_type ADD VALUE IF NOT EXISTS 'not_provided'")
    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("phone_number", sa.String(16), nullable=False, unique=True),
        sa.Column("client_type", client_type, nullable=False, server_default="random"),
        sa.Column("display_name", sa.String(160)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("phone_number ~ '^\\+[1-9][0-9]{7,14}$'", name="ck_clients_phone_e164"),
    )
    op.create_index("ix_clients_phone_number", "clients", ["phone_number"])
    op.create_table(
        "external_managers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("phone_number", sa.String(16), nullable=False, unique=True),
        sa.Column("mode", manager_mode, nullable=False),
        sa.Column("document_types", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("schedule_start", sa.Time()),
        sa.Column("schedule_end", sa.Time()),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Mexico_City"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "phone_number ~ '^\\+[1-9][0-9]{7,14}$'", name="ck_external_managers_phone_e164"
        ),
    )
    op.create_index("ix_external_managers_phone_number", "external_managers", ["phone_number"])
    op.execute(
        "INSERT INTO clients (id, phone_number, client_type) "
        "SELECT id, phone_number, 'fixed' FROM users WHERE role='client' "
        "ON CONFLICT DO NOTHING"
    )
    op.execute(
        "INSERT INTO external_managers (id, name, phone_number, mode) "
        "SELECT id, 'Gestor migrado', phone_number, 'fallback' FROM users "
        "WHERE role='gestor' ON CONFLICT DO NOTHING"
    )
    op.drop_constraint("fk_documents_uploaded_by_users", "documents", type_="foreignkey")
    op.create_foreign_key(
        "fk_documents_uploaded_by_external_managers",
        "documents",
        "external_managers",
        ["uploaded_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("fk_requests_client_id_users", "requests", type_="foreignkey")
    op.drop_constraint("fk_requests_gestor_id_users", "requests", type_="foreignkey")
    op.create_foreign_key(
        "fk_requests_client_id_clients",
        "requests",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_requests_gestor_id_external_managers",
        "requests",
        "external_managers",
        ["gestor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("requests", "identifier_encrypted", nullable=True)
    op.alter_column("requests", "identifier_hash", nullable=True)
    op.alter_column(
        "requests",
        "identifier_masked",
        type_=sa.String(80),
        existing_type=sa.String(24),
        server_default="",
    )
    op.add_column(
        "requests", sa.Column("service_type", sa.String(80), nullable=False, server_default="other")
    )
    op.add_column(
        "requests",
        sa.Column("original_message", sa.String(2000), nullable=False, server_default=""),
    )
    op.add_column("requests", sa.Column("assignment_reason", sa.String(80)))


def downgrade() -> None:
    raise RuntimeError(
        "Operational identity migration is intentionally irreversible; restore a backup"
    )
