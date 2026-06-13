"""drop unused pay_periods table and bill_instances.pay_period_id

The PayPeriod model was never wired into the schedule service; pay_period_id
has always been NULL in every bill_instances row. Both the column and the table
are dead weight.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("bill_instances") as batch_op:
        batch_op.drop_index("ix_bill_instances_pay_period_id")
        batch_op.drop_column("pay_period_id")

    op.drop_index("ix_pay_periods_pay_date", "pay_periods")
    op.drop_table("pay_periods")


def downgrade() -> None:
    op.create_table(
        "pay_periods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("pay_date", sa.Date(), nullable=False),
        sa.Column("opening_balance", sa.Numeric(10, 2), nullable=False),
        sa.Column("closing_balance", sa.Numeric(10, 2), nullable=True),
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
    )
    op.create_index("ix_pay_periods_pay_date", "pay_periods", ["pay_date"])

    with op.batch_alter_table("bill_instances") as batch_op:
        batch_op.add_column(
            sa.Column("pay_period_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index(
            "ix_bill_instances_pay_period_id", ["pay_period_id"]
        )
