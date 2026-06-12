from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils import utcnow


class PayPeriodActual(Base):
    """Confirmed actuals for a payday — the real deposit and/or account balance.

    Used to re-anchor the rolling-balance projection so carried-forward
    "available to spend" doesn't compound estimation error every period. Both
    fields are optional (balance is the high-value one). Mirrors the
    ``PayPeriodOverride`` pattern: one row per pay date.
    """

    __tablename__ = "pay_period_actuals"

    id: Mapped[int] = mapped_column(primary_key=True)
    pay_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    # Actual net pay deposited this payday (overrides the assumed salary for
    # this period only).
    actual_net_pay: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    # Actual account balance *after* the deposit. When set, it becomes this
    # period's opening balance and the projection rolls forward from there.
    actual_balance: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )


__all__ = ["PayPeriodActual"]
