"""Add revocable portal grants and download audit events."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260804_0004"
down_revision: str | None = "20260804_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    status = sa.Enum("active", "revoked", "expired", name="portal_grant_status")
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "portal_access_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("status", status, server_default="active", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_portal_access_grants_request_id", "portal_access_grants", ["request_id"])
    op.create_index("ix_portal_access_grants_token_hash", "portal_access_grants", ["token_hash"])
    op.create_index("ix_portal_access_grants_expires_at", "portal_access_grants", ["expires_at"])
    op.create_table(
        "document_download_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("grant_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["grant_id"], ["portal_access_grants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("grant_id", "request_id", "document_id", "occurred_at"):
        op.create_index(
            f"ix_document_download_events_{column}", "document_download_events", [column]
        )


def downgrade() -> None:
    for column in ("occurred_at", "document_id", "request_id", "grant_id"):
        op.drop_index(
            f"ix_document_download_events_{column}", table_name="document_download_events"
        )
    op.drop_table("document_download_events")
    op.drop_index("ix_portal_access_grants_expires_at", table_name="portal_access_grants")
    op.drop_index("ix_portal_access_grants_token_hash", table_name="portal_access_grants")
    op.drop_index("ix_portal_access_grants_request_id", table_name="portal_access_grants")
    op.drop_table("portal_access_grants")
    sa.Enum(name="portal_grant_status").drop(op.get_bind(), checkfirst=True)
