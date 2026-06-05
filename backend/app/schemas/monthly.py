from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class MonthlyBillItem(BaseModel):
    bill_id: int
    name: str
    due_date: date
    amount: Decimal  # scheduled (estimated) amount
    category: str
    is_variable: bool = False
    status: str = "on_time"
    actual_amount: Decimal | None = None


class MonthlyCategoryGroup(BaseModel):
    category: str
    subtotal: Decimal
    bills: list[MonthlyBillItem]


class MonthlySummary(BaseModel):
    month: str  # "YYYY-MM"
    total_income: Decimal
    total_bills: Decimal
    available: Decimal
    categories: list[MonthlyCategoryGroup]


class MonthlySummaryResponse(BaseModel):
    months: list[MonthlySummary]
