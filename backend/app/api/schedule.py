from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bill, BillInstance, PaySchedule
from app.models.enums import BillRecurrence, BillStatus, PayFrequency
from app.models.pay_period_override import PayPeriodOverride
from app.schemas.monthly import (
    MonthlyBillItem,
    MonthlyCategoryGroup,
    MonthlySummary,
    MonthlySummaryResponse,
)
from app.schemas.schedule import (
    AssignedBillOut,
    PayPeriodOut,
    ScheduleResponse,
    ScheduleSummary,
)
from app.services.pay_period_engine import (
    BillInput,
    PayPeriodResult,
    build_periods,
    due_dates_for_bill,
    project,
)

# Keyed by (bill_id, due_date)
_InstanceMap = dict[tuple[int, date], BillInstance]
# Keyed by original (computed) pay_date → overridden pay_date
_OverrideMap = dict[date, date]

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


_BillIsVariable = dict[int, bool]
_BillCategory = dict[int, str]


def _to_period_out(
    p: PayPeriodResult,
    instances: _InstanceMap,
    bill_is_variable: _BillIsVariable,
    bill_category: _BillCategory,
    override_map: _OverrideMap,
) -> PayPeriodOut:
    bills_out: list[AssignedBillOut] = []
    for b in p.assigned_bills:
        inst = instances.get((b.bill_id, b.due_date))
        if inst is not None and inst.status in (BillStatus.paid, BillStatus.skipped):
            effective_status = inst.status
        else:
            effective_status = b.status
        bills_out.append(
            AssignedBillOut(
                bill_id=b.bill_id,
                name=b.name,
                due_date=b.due_date,
                amount=b.amount,
                status=effective_status,
                instance_id=inst.id if inst else None,
                actual_amount=inst.actual_amount if inst else None,
                is_variable=bill_is_variable.get(b.bill_id, False),
                category=bill_category.get(b.bill_id, "other"),
            )
        )

    def _effective_amount(bo: AssignedBillOut) -> Decimal:
        if bo.actual_amount is not None:
            return Decimal(str(bo.actual_amount))
        return bo.amount

    total = sum(
        (_effective_amount(bo) for bo in bills_out if bo.status != BillStatus.skipped),
        Decimal("0"),
    )
    remaining = p.opening_balance - total
    flagged = sum(1 for bo in bills_out if bo.status == "late_flagged")
    effective_pay_date = override_map.get(p.pay_date, p.pay_date)
    return PayPeriodOut(
        period_index=p.period_index,
        pay_date=effective_pay_date,
        original_pay_date=p.pay_date,
        is_overridden=p.pay_date in override_map,
        period_start=p.period_start,
        period_end=p.period_end,
        opening_balance=p.opening_balance,
        total_bills=total,
        remaining_balance=remaining,
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

    bill_rows = db.query(Bill).filter(Bill.is_active.is_(True)).all()
    bill_is_variable: _BillIsVariable = {b.id: b.is_variable for b in bill_rows}
    bill_category: _BillCategory = {b.id: b.category for b in bill_rows}
    bills = [_to_bill_input(b) for b in bill_rows]

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

    # Load BillInstance records and pay-date overrides for this window
    instances: _InstanceMap = {}
    override_map: _OverrideMap = {}
    if window:
        window_start = window[0].period_start
        window_end = window[-1].period_end
        rows = (
            db.query(BillInstance)
            .filter(
                BillInstance.due_date >= window_start,
                BillInstance.due_date <= window_end,
            )
            .all()
        )
        instances = {(r.bill_id, r.due_date): r for r in rows}

        pay_dates = [p.pay_date for p in window]
        override_rows = (
            db.query(PayPeriodOverride)
            .filter(PayPeriodOverride.original_pay_date.in_(pay_dates))
            .all()
        )
        override_map = {
            r.original_pay_date: r.overridden_pay_date for r in override_rows
        }

    period_outs = [
        _to_period_out(p, instances, bill_is_variable, bill_category, override_map)
        for p in window
    ]

    total_flagged = sum(
        1 for p in period_outs for b in p.assigned_bills if b.status == "late_flagged"
    )
    effective_from = window[0].period_start if window else today
    effective_to = window[-1].period_end if window else today

    return ScheduleResponse(
        periods=period_outs,
        summary=ScheduleSummary(
            from_date=effective_from,
            to_date=effective_to,
            period_count=len(window),
            total_flagged_bills=total_flagged,
        ),
    )


# ---------------------------------------------------------------------------
# Monthly summary helpers
# ---------------------------------------------------------------------------

_CATEGORY_ORDER = [
    "housing",
    "utilities",
    "subscriptions",
    "insurance",
    "debt",
    "savings",
    "other",
]


def _parse_year_month(value: str) -> tuple[int, int]:
    parts = value.split("-")
    if len(parts) != 2:
        raise ValueError("expected YYYY-MM")
    year, month = int(parts[0]), int(parts[1])
    if not 1 <= month <= 12:
        raise ValueError("month must be 1-12")
    return year, month


def _month_last_day(year: int, month: int) -> date:
    _, last = monthrange(year, month)
    return date(year, month, last)


def _months_in_range(
    from_year: int, from_month: int, to_year: int, to_month: int
) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    y, m = from_year, from_month
    while (y, m) <= (to_year, to_month):
        months.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return months


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
def get_monthly_summary(
    from_month: str | None = Query(default=None, alias="from"),
    to_month: str | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> MonthlySummaryResponse:
    sched = db.query(PaySchedule).first()
    if sched is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pay schedule configured",
        )

    today = date.today()

    try:
        from_year, from_m = (
            _parse_year_month(from_month) if from_month else (today.year, today.month)
        )
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'from' must be YYYY-MM",
        )

    try:
        if to_month:
            to_year, to_m = _parse_year_month(to_month)
        else:
            # default: from_month + 2 (3 months total)
            raw = from_m + 2
            to_year = from_year + (raw - 1) // 12
            to_m = (raw - 1) % 12 + 1
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'to' must be YYYY-MM",
        )

    if (to_year, to_m) < (from_year, from_m):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'to' must be >= 'from'",
        )

    window_start = date(from_year, from_m, 1)
    window_end = _month_last_day(to_year, to_m)

    frequency = PayFrequency(sched.frequency)
    first_paycheck = sched.first_paycheck_date
    net_salary = Decimal(str(sched.net_salary))

    # Income per month: count pay periods whose period_start falls in the window
    num_needed = _periods_needed(first_paycheck, window_end, frequency)
    all_pay_periods = build_periods(first_paycheck, frequency, num_needed)
    income_by_month: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    for p in all_pay_periods:
        if window_start <= p.period_start <= window_end:
            key = (p.period_start.year, p.period_start.month)
            income_by_month[key] += net_salary

    # Bills per month: find all due dates in the window
    bill_rows = db.query(Bill).filter(Bill.is_active.is_(True)).all()
    bills_by_month: dict[tuple[int, int], list[tuple[Bill, date]]] = defaultdict(list)
    for bill in bill_rows:
        bill_input = _to_bill_input(bill)
        for due_date in due_dates_for_bill(bill_input, window_start, window_end):
            key = (due_date.year, due_date.month)
            bills_by_month[key].append((bill, due_date))

    # Payment-status overlay: actual amounts and paid/skipped status, matching
    # the pay-period view so the same bill totals the same in both views.
    instance_rows = (
        db.query(BillInstance)
        .filter(
            BillInstance.due_date >= window_start,
            BillInstance.due_date <= window_end,
        )
        .all()
    )
    instances: _InstanceMap = {(r.bill_id, r.due_date): r for r in instance_rows}

    def _build_item(bill: Bill, due_date: date) -> MonthlyBillItem:
        inst = instances.get((bill.id, due_date))
        status_ = (
            inst.status
            if inst is not None and inst.status in (BillStatus.paid, BillStatus.skipped)
            else "on_time"
        )
        return MonthlyBillItem(
            bill_id=bill.id,
            name=bill.name,
            due_date=due_date,
            amount=Decimal(str(bill.estimated_amount)),
            category=bill.category,
            is_variable=bill.is_variable,
            status=status_,
            actual_amount=inst.actual_amount if inst is not None else None,
        )

    def _effective_amount(item: MonthlyBillItem) -> Decimal:
        """Skipped bills count as 0; paid bills use actual when recorded."""
        if item.status == BillStatus.skipped:
            return Decimal("0")
        if item.actual_amount is not None:
            return Decimal(str(item.actual_amount))
        return item.amount

    # Build one MonthlySummary per month
    result: list[MonthlySummary] = []
    for y, m in _months_in_range(from_year, from_m, to_year, to_m):
        key = (y, m)
        total_income = income_by_month.get(key, Decimal("0"))
        month_bills = bills_by_month.get(key, [])

        cat_map: dict[str, list[MonthlyBillItem]] = defaultdict(list)
        for bill, due_date in month_bills:
            cat_map[bill.category].append(_build_item(bill, due_date))

        total_bills = sum(
            (_effective_amount(item) for items in cat_map.values() for item in items),
            Decimal("0"),
        )
        available = total_income - total_bills

        categories = [
            MonthlyCategoryGroup(
                category=cat,
                subtotal=sum(
                    (_effective_amount(i) for i in cat_map[cat]),
                    Decimal("0"),
                ),
                bills=sorted(cat_map[cat], key=lambda i: i.due_date),
            )
            for cat in _CATEGORY_ORDER
            if cat in cat_map
        ]

        result.append(
            MonthlySummary(
                month=f"{y:04d}-{m:02d}",
                total_income=total_income,
                total_bills=total_bills,
                available=available,
                categories=categories,
            )
        )

    return MonthlySummaryResponse(months=result)
