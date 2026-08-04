"""Add antimalware quarantine state and scan metadata."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260804_0006"
down_revision: str | None = "20260804_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for value in ("quarantined", "clean", "infected", "scan_failed"):
        op.execute(f"ALTER TYPE document_status ADD VALUE IF NOT EXISTS '{value}'")
    op.add_column(
        "documents",
        sa.Column("scan_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("documents", sa.Column("scan_engine", sa.String(64)))
    op.add_column("documents", sa.Column("scan_signature", sa.String(255)))
    op.add_column("documents", sa.Column("scanned_at", sa.DateTime(timezone=True)))
    op.add_column("documents", sa.Column("next_scan_at", sa.DateTime(timezone=True)))
    op.create_index("ix_documents_scanned_at", "documents", ["scanned_at"])
    op.create_index("ix_documents_next_scan_at", "documents", ["next_scan_at"])
    op.execute(
        "UPDATE documents SET status = 'quarantined', next_scan_at = now() "
        "WHERE status IN ('received', 'validated', 'ready') AND deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE documents SET status = 'rejected' "
        "WHERE status IN ('quarantined', 'infected', 'scan_failed')"
    )
    op.execute("UPDATE documents SET status = 'validated' WHERE status = 'clean'")
    op.drop_index("ix_documents_next_scan_at", table_name="documents")
    op.drop_index("ix_documents_scanned_at", table_name="documents")
    for column in (
        "next_scan_at",
        "scanned_at",
        "scan_signature",
        "scan_engine",
        "scan_attempts",
    ):
        op.drop_column("documents", column)
