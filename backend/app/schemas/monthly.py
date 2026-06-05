from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class MonthlyBillItem(BaseModel):
    bill_id: int
    name: str
    due_date: date
    amount: Decimal
    category: str
    is_variable: bool = False


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
