from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class AssignedBillOut(BaseModel):
    bill_id: int
    name: str
    due_date: date
    amount: Decimal
    status: str
    instance_id: int | None = None
    actual_amount: Decimal | None = None
    is_variable: bool = False
    category: str = "other"


class PayPeriodOut(BaseModel):
    period_index: int
    pay_date: date
    original_pay_date: date
    is_overridden: bool = False
    period_start: date
    period_end: date
    opening_balance: Decimal
    total_bills: Decimal
    remaining_balance: Decimal
    flagged_bill_count: int
    assigned_bills: list[AssignedBillOut]


class ScheduleSummary(BaseModel):
    from_date: date
    to_date: date
    period_count: int
    total_flagged_bills: int


class ScheduleResponse(BaseModel):
    periods: list[PayPeriodOut]
    summary: ScheduleSummary
