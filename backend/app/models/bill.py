from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import BillCategory, BillRecurrence
from app.utils import utcnow

if TYPE_CHECKING:
    from app.models.bill_instance import BillInstance


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    recurrence: Mapped[str] = mapped_column(String)
    due_day: Mapped[int | None] = mapped_column(Integer)
    first_due_date: Mapped[date | None] = mapped_column(Date)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    category: Mapped[str] = mapped_column(String)
    is_variable: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
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

    instances: Mapped[list[BillInstance]] = relationship(
        "BillInstance", back_populates="bill", cascade="all, delete-orphan"
    )


__all__ = ["Bill", "BillCategory", "BillRecurrence"]
