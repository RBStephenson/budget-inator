from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import BillStatus
from app.utils import utcnow

if TYPE_CHECKING:
    from app.models.bill import Bill


class BillInstance(Base):
    __tablename__ = "bill_instances"
    __table_args__ = (UniqueConstraint("bill_id", "due_date", name="uq_bill_instance"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(
        ForeignKey("bills.id", ondelete="CASCADE"), index=True
    )
    due_date: Mapped[date] = mapped_column(Date)
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    actual_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(
        String, default=BillStatus.pending, server_default=text("'pending'")
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    bill: Mapped[Bill] = relationship("Bill", back_populates="instances")


__all__ = ["BillInstance", "BillStatus"]
