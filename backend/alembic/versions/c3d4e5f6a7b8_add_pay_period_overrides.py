"""add pay_period_overrides table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pay_period_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_pay_date", sa.Date(), nullable=False),
        sa.Column("overridden_pay_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("original_pay_date", name="uq_pay_period_override_date"),
    )
    op.create_index(
        "ix_pay_period_overrides_original_pay_date",
        "pay_period_overrides",
        ["original_pay_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pay_period_overrides_original_pay_date", "pay_period_overrides"
    )
    op.drop_table("pay_period_overrides")
