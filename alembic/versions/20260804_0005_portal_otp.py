"""Add one-time verification and lockout to portal grants."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260804_0005"
down_revision: str | None = "20260804_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("portal_access_grants", sa.Column("otp_hash", sa.String(64)))
    op.add_column(
        "portal_access_grants",
        sa.Column("otp_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("portal_access_grants", sa.Column("otp_expires_at", sa.DateTime(timezone=True)))
    op.add_column("portal_access_grants", sa.Column("otp_verified_at", sa.DateTime(timezone=True)))
    op.add_column("portal_access_grants", sa.Column("locked_until", sa.DateTime(timezone=True)))
    op.execute(
        "UPDATE portal_access_grants SET otp_hash = repeat('0', 64), "
        "otp_expires_at = now(), status = 'expired'"
    )
    op.alter_column("portal_access_grants", "otp_hash", nullable=False)
    op.alter_column("portal_access_grants", "otp_expires_at", nullable=False)
    op.create_index(
        "ix_portal_access_grants_otp_expires_at",
        "portal_access_grants",
        ["otp_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_access_grants_otp_expires_at", table_name="portal_access_grants")
    for column in (
        "locked_until",
        "otp_verified_at",
        "otp_expires_at",
        "otp_attempts",
        "otp_hash",
    ):
        op.drop_column("portal_access_grants", column)
