from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bill, PaySchedule
from app.models.enums import BillRecurrence, PayFrequency
from app.schemas.schedule import (
    AssignedBillOut,
    PayPeriodOut,
    ScheduleResponse,
    ScheduleSummary,
)
from app.services.pay_period_engine import BillInput, PayPeriodResult, project

router = APIRouter(prefix="/schedule", tags=["schedule"])

_MIN_PERIOD_DAYS: dict[PayFrequency, int] = {
    PayFrequency.weekly: 7,
    PayFrequency.biweekly: 14,
    PayFrequency.semimonthly: 13,
    PayFrequency.monthly: 28,
}


def _periods_needed(first_paycheck: date, target: date, frequency: PayFrequency) -> int:
    """Conservative upper bound on periods needed to reach *target*."""
    delta = max(0, (target - first_paycheck).days)
    return delta // _MIN_PERIOD_DAYS[frequency] + 5


def _find_current_index(periods: list[PayPeriodResult], today: date) -> int:
    """Index of the period containing *today*, or the first future period."""
    for i, p in enumerate(periods):
        if p.period_start <= today <= p.period_end:
            return i
        if p.period_start > today:
            return i
    return max(0, len(periods) - 1)


def _to_bill_input(bill: Bill) -> BillInput:
    return BillInput(
        id=bill.id,
        name=bill.name,
        amount=Decimal(str(bill.estimated_amount)),
        recurrence=BillRecurrence(bill.recurrence),
        due_day=bill.due_day,
        first_due_date=bill.first_due_date,
        grace_period_days=bill.grace_period_days,
    )


def _to_period_out(p: PayPeriodResult) -> PayPeriodOut:
    bills_out = [
        AssignedBillOut(
            bill_id=b.bill_id,
            name=b.name,
            due_date=b.due_date,
            amount=b.amount,
            status=b.status,
        )
        for b in p.assigned_bills
    ]
    total = sum((b.amount for b in p.assigned_bills), Decimal("0"))
    flagged = sum(1 for b in p.assigned_bills if b.status == "late_flagged")
    return PayPeriodOut(
        period_index=p.period_index,
        pay_date=p.pay_date,
        period_start=p.period_start,
        period_end=p.period_end,
        opening_balance=p.opening_balance,
        total_bills=total,
        remaining_balance=p.remaining_balance,
        flagged_bill_count=flagged,
        assigned_bills=bills_out,
    )


@router.get("", response_model=ScheduleResponse)
def get_schedule(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    sched = db.query(PaySchedule).first()
    if sched is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pay schedule configured",
        )

    frequency = PayFrequency(sched.frequency)
    first_paycheck = sched.first_paycheck_date
    net_salary = Decimal(str(sched.net_salary))
    beginning_balance = Decimal(str(sched.beginning_balance))

    bills = [
        _to_bill_input(b) for b in db.query(Bill).filter(Bill.is_active.is_(True)).all()
    ]

    today = date.today()

    if from_date is None and to_date is None:
        # Generate enough periods to find today + 3 more
        num_needed = _periods_needed(first_paycheck, today, frequency) + 4
        all_periods = project(
            first_paycheck, frequency, num_needed, net_salary, beginning_balance, bills
        )
        current_idx = _find_current_index(all_periods, today)
        window = all_periods[current_idx : current_idx + 4]
    else:
        if from_date is None:
            from_date = today
        if to_date is None:
            to_date = from_date

        if to_date < from_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="'to' must be >= 'from'",
            )

        num_needed = _periods_needed(first_paycheck, to_date, frequency)
        all_periods = project(
            first_paycheck, frequency, num_needed, net_salary, beginning_balance, bills
        )
        # Include periods that overlap [from_date, to_date]
        window = [
            p
            for p in all_periods
            if p.period_end >= from_date and p.period_start <= to_date
        ]

    if not window:
        window = []

    total_flagged = sum(
        1 for p in window for b in p.assigned_bills if b.status == "late_flagged"
    )
    effective_from = window[0].period_start if window else today
    effective_to = window[-1].period_end if window else today

    return ScheduleResponse(
        periods=[_to_period_out(p) for p in window],
        summary=ScheduleSummary(
            from_date=effective_from,
            to_date=effective_to,
            period_count=len(window),
            total_flagged_bills=total_flagged,
        ),
    )
