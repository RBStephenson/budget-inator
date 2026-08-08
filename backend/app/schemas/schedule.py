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
    placement_source: str = "inferred"
    manual_pay_date: date | None = None
    is_carried_over: bool = False
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
    total_paid: Decimal = Decimal("0")
    total_unpaid: Decimal = Decimal("0")
    total_sinking_funds: Decimal = Decimal("0")
    remaining_balance: Decimal
    period_result: Decimal
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
    buffer_balance: Decimal = Decimal("0")


class ScheduleResponse(BaseModel):
    periods: list[PayPeriodOut]
    summary: ScheduleSummary


class RebalancePreviewRequest(BaseModel):
    source_pay_date: date
    max_moves: int = Field(default=5, ge=1, le=20)


class RebalanceMove(BaseModel):
    bill_id: int
    name: str
    due_date: date
    amount: Decimal
    from_pay_date: date
    to_pay_date: date
    from_period_remaining_before: Decimal
    from_period_remaining_after: Decimal
    source_remaining_before: Decimal
    source_remaining_after: Decimal
    reason: str


class RebalancePreviewResponse(BaseModel):
    source_pay_date: date
    source_remaining_before: Decimal
    source_remaining_after: Decimal
    moves: list[RebalanceMove]


class RebalanceApplyRequest(BaseModel):
    moves: list[RebalanceMove]


class SmoothingPreviewRequest(BaseModel):
    source_pay_date: date
