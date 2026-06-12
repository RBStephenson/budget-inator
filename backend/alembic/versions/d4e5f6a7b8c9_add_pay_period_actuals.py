"""add pay_period_actuals table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pay_period_actuals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pay_date", sa.Date(), nullable=False),
        sa.Column("actual_net_pay", sa.Numeric(10, 2), nullable=True),
        sa.Column("actual_balance", sa.Numeric(10, 2), nullable=True),
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
        sa.UniqueConstraint("pay_date", name="uq_pay_period_actual_date"),
    )
    op.create_index(
        "ix_pay_period_actuals_pay_date",
        "pay_period_actuals",
        ["pay_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_pay_period_actuals_pay_date", "pay_period_actuals")
    op.drop_table("pay_period_actuals")
