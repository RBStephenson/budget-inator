from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


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
    sinking_fund_applied: Decimal = Decimal("0")
    sinking_fund_shortfall: Decimal = Decimal("0")


class SinkingFundContributionOut(BaseModel):
    bill_id: int
    name: str
    next_due_date: date
    target_amount: Decimal
    saved_amount: Decimal
    contribution_amount: Decimal
    shortfall_amount: Decimal
    surplus_amount: Decimal


class PayPeriodOut(BaseModel):
    period_index: int
    pay_date: date
    original_pay_date: date
    is_overridden: bool = False
    period_start: date
    period_end: date
    opening_balance: Decimal
    total_bills: Decimal
    total_sinking_funds: Decimal = Decimal("0")
    remaining_balance: Decimal
    flagged_bill_count: int
    assigned_bills: list[AssignedBillOut]
    sinking_fund_contributions: list[SinkingFundContributionOut] = Field(
        default_factory=list
    )


class ScheduleSummary(BaseModel):
    from_date: date
    to_date: date
    period_count: int
    total_flagged_bills: int


class ScheduleResponse(BaseModel):
    periods: list[PayPeriodOut]
    summary: ScheduleSummary
