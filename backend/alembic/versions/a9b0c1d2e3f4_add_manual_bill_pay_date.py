"""add manual bill pay date

Revision ID: a9b0c1d2e3f4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("bill_instances") as batch_op:
        batch_op.add_column(sa.Column("manual_pay_date", sa.Date(), nullable=True))
        batch_op.create_index(
            "ix_bill_instances_manual_pay_date",
            ["manual_pay_date"],
        )


def downgrade() -> None:
    with op.batch_alter_table("bill_instances") as batch_op:
        batch_op.drop_index("ix_bill_instances_manual_pay_date")
        batch_op.drop_column("manual_pay_date")
