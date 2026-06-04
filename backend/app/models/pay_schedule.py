from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import PayFrequency
from app.utils import utcnow


class PaySchedule(Base):
    __tablename__ = "pay_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    net_salary: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    first_paycheck_date: Mapped[date] = mapped_column(Date)
    beginning_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    frequency: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )


__all__ = ["PayFrequency", "PaySchedule"]
