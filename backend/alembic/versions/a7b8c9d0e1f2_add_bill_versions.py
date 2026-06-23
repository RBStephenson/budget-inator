"""add bill versions

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bill_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("estimated_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("recurrence", sa.String(), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column(
            "due_day_is_month_end",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("first_due_date", sa.Date(), nullable=True),
        sa.Column(
            "grace_period_days",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column(
            "is_variable", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False
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
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bill_id", "effective_date", name="uq_bill_version_date"),
    )
    op.create_index(
        op.f("ix_bill_versions_bill_id"), "bill_versions", ["bill_id"], unique=False
    )
    op.create_index(
        op.f("ix_bill_versions_effective_date"),
        "bill_versions",
        ["effective_date"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO bill_versions (
            bill_id,
            effective_date,
            name,
            estimated_amount,
            recurrence,
            due_day,
            due_day_is_month_end,
            first_due_date,
            grace_period_days,
            category,
            is_variable,
            is_active,
            notes,
            created_at,
            updated_at
        )
        SELECT
            id,
            '0001-01-01',
            name,
            estimated_amount,
            recurrence,
            due_day,
            due_day_is_month_end,
            first_due_date,
            grace_period_days,
            category,
            is_variable,
            is_active,
            notes,
            created_at,
            updated_at
        FROM bills
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_bill_versions_effective_date"), table_name="bill_versions")
    op.drop_index(op.f("ix_bill_versions_bill_id"), table_name="bill_versions")
    op.drop_table("bill_versions")
