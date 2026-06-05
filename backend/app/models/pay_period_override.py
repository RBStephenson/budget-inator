from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils import utcnow


class PayPeriodOverride(Base):
    __tablename__ = "pay_period_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_pay_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    overridden_pay_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )


__all__ = ["PayPeriodOverride"]
