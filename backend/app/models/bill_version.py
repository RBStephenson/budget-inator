from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import utcnow

if TYPE_CHECKING:
    from app.models.bill import Bill


class BillVersion(Base):
    __tablename__ = "bill_versions"
    __table_args__ = (
        UniqueConstraint("bill_id", "effective_date", name="uq_bill_version_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(
        ForeignKey("bills.id", ondelete="CASCADE"), index=True
    )
    effective_date: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str] = mapped_column(String)
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    recurrence: Mapped[str] = mapped_column(String)
    due_day: Mapped[int | None] = mapped_column(Integer)
    due_day_is_month_end: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0")
    )
    first_due_date: Mapped[date | None] = mapped_column(Date)
    grace_period_days: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )
    category: Mapped[str] = mapped_column(String)
    is_variable: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0")
    )
    sinking_fund_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    bill: Mapped[Bill] = relationship("Bill", back_populates="versions")


__all__ = ["BillVersion"]
