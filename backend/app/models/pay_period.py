from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import utcnow

if TYPE_CHECKING:
    from app.models.bill_instance import BillInstance


class PayPeriod(Base):
    __tablename__ = "pay_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    pay_date: Mapped[date] = mapped_column(Date, index=True)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    bill_instances: Mapped[list[BillInstance]] = relationship(
        "BillInstance", back_populates="pay_period", cascade="all, delete-orphan"
    )


__all__ = ["PayPeriod"]
