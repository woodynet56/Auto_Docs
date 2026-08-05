"""Add durable delivery outbox and message traceability.

Revision ID: 20260804_0003
Revises: 20260804_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260804_0003"
down_revision: str | None = "20260804_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    delivery_status = sa.Enum("pending", "processing", "sent", "failed", name="delivery_status")
    delivery_status.create(op.get_bind(), checkfirst=True)
    op.add_column("documents", sa.Column("delivery_message_id", sa.String(255)))
    op.create_table(
        "delivery_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("status", delivery_status, server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("provider_message_id", sa.String(255)),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_delivery_attempt_request"),
        sa.UniqueConstraint("provider_message_id"),
    )
    op.create_index("ix_delivery_attempts_request_id", "delivery_attempts", ["request_id"])
    op.create_index(
        "ix_delivery_attempts_next_attempt_at", "delivery_attempts", ["next_attempt_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_attempts_next_attempt_at", table_name="delivery_attempts")
    op.drop_index("ix_delivery_attempts_request_id", table_name="delivery_attempts")
    op.drop_table("delivery_attempts")
    op.drop_column("documents", "delivery_message_id")
    sa.Enum(name="delivery_status").drop(op.get_bind(), checkfirst=True)
