"""initial schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pay_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("net_salary", sa.Numeric(10, 2), nullable=False),
        sa.Column("first_paycheck_date", sa.Date(), nullable=False),
        sa.Column("beginning_balance", sa.Numeric(10, 2), nullable=False),
        sa.Column("frequency", sa.String(), nullable=False),
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

    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("estimated_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("recurrence", sa.String(), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("first_due_date", sa.Date(), nullable=True),
        sa.Column(
            "grace_period_days",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column(
            "is_variable",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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

    op.create_table(
        "bill_instances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("pay_period_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("estimated_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("actual_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
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
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pay_period_id"], ["pay_periods.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bill_id", "due_date", name="uq_bill_instance"),
    )
    op.create_index("ix_bill_instances_bill_id", "bill_instances", ["bill_id"])
    op.create_index(
        "ix_bill_instances_pay_period_id", "bill_instances", ["pay_period_id"]
    )


def downgrade() -> None:
    op.drop_table("bill_instances")
    op.drop_index("ix_pay_periods_pay_date", "pay_periods")
    op.drop_table("pay_periods")
    op.drop_table("bills")
    op.drop_table("pay_schedules")
