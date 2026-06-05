"""make bill_instances.pay_period_id nullable

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("bill_instances") as batch_op:
        batch_op.alter_column(
            "pay_period_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("bill_instances") as batch_op:
        batch_op.alter_column(
            "pay_period_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
