from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.models.enums import BillRecurrence, PayFrequency

# ---------------------------------------------------------------------------
# Input / output types
# ---------------------------------------------------------------------------


@dataclass
class BillInput:
    id: int
    name: str
    amount: Decimal
    recurrence: BillRecurrence
    due_day: int | None  # month-day for monthly bills (1–28)
    first_due_date: date | None  # anchor date for non-monthly bills
    grace_period_days: int = 0


@dataclass
class AssignedBill:
    bill_id: int
    name: str
    due_date: date
    amount: Decimal
    status: str  # "on_time" | "late_flagged"


@dataclass
class PayPeriodResult:
    period_index: int
    pay_date: date
    period_start: date
    period_end: date
    opening_balance: Decimal
    assigned_bills: list[AssignedBill] = field(default_factory=list)

    @property
    def remaining_balance(self) -> Decimal:
        return self.opening_balance - sum(b.amount for b in self.assigned_bills)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, _days_in_month(year, month))
    return date(year, month, day)


def _next_pay_date(current: date, frequency: PayFrequency) -> date:
    if frequency == PayFrequency.weekly:
        return current + timedelta(days=7)
    if frequency == PayFrequency.biweekly:
        return current + timedelta(days=14)
    if frequency == PayFrequency.semimonthly:
        # 1st → 15th of same month; 15th → 1st of next month
        if current.day < 15:
            return current.replace(day=15)
        return _add_months(current.replace(day=1), 1)
    # monthly
    return _add_months(current, 1)


# ---------------------------------------------------------------------------
# Period generation
# ---------------------------------------------------------------------------


def build_periods(
    first_paycheck_date: date,
    frequency: PayFrequency,
    num_periods: int,
) -> list[PayPeriodResult]:
    """Generate *num_periods* pay periods (boundaries only; balances set separately)."""
    # Need num_periods + 1 pay dates to know each period's end date.
    pay_dates: list[date] = [first_paycheck_date]
    for _ in range(num_periods):
        pay_dates.append(_next_pay_date(pay_dates[-1], frequency))

    return [
        PayPeriodResult(
            period_index=i,
            pay_date=pay_dates[i],
            period_start=pay_dates[i],
            period_end=pay_dates[i + 1] - timedelta(days=1),
            opening_balance=Decimal("0"),
        )
        for i in range(num_periods)
    ]


def apply_rolling_balances(
    periods: list[PayPeriodResult],
    net_salary: Decimal,
    beginning_balance: Decimal,
) -> None:
    """
    Set opening_balance on each period using rolling carry-over.

    Period 0 opens with beginning_balance + net_salary.
    Each subsequent period opens with previous remaining_balance + net_salary.
    Must be called AFTER bills are assigned so remaining_balance is accurate.
    """
    for i, p in enumerate(periods):
        if i == 0:
            p.opening_balance = beginning_balance + net_salary
        else:
            p.opening_balance = periods[i - 1].remaining_balance + net_salary


# ---------------------------------------------------------------------------
# Bill due-date generation
# ---------------------------------------------------------------------------


def _biweekly_or_weekly_dates(
    anchor: date, delta: timedelta, window_start: date, window_end: date
) -> list[date]:
    """
    Occurrences of the sequence anchor, anchor+delta, anchor+2*delta, ...
    that fall within [window_start, window_end].

    anchor is the FIRST due date; the sequence never goes before it.
    """
    d = anchor
    # Advance past window_start if needed
    while d < window_start:
        d += delta
    dates = []
    while d <= window_end:
        dates.append(d)
        d += delta
    return dates


def _anchor_recurrence_dates(
    anchor: date, months: int, window_start: date, window_end: date
) -> list[date]:
    """All occurrences of anchor + k*months in [window_start, window_end]."""
    d = anchor
    # Walk forward to first occurrence >= window_start
    while d < window_start:
        d = _add_months(d, months)
    dates = []
    while d <= window_end:
        dates.append(d)
        d = _add_months(d, months)
    return dates


def due_dates_for_bill(
    bill: BillInput, window_start: date, window_end: date
) -> list[date]:
    """All due dates for *bill* that fall within [window_start, window_end]."""
    r = bill.recurrence

    if r == BillRecurrence.monthly:
        assert bill.due_day is not None
        due_day = bill.due_day
        dates: list[date] = []
        # First candidate: due_day in window_start's month, clamped to actual days
        clamp = _days_in_month(window_start.year, window_start.month)
        d = date(window_start.year, window_start.month, min(due_day, clamp))
        if d < window_start:
            d = _add_months(d, 1)
            d = d.replace(day=min(due_day, _days_in_month(d.year, d.month)))
        while d <= window_end:
            dates.append(d)
            d = _add_months(d, 1)
            d = d.replace(day=min(due_day, _days_in_month(d.year, d.month)))
        return dates

    if r == BillRecurrence.biweekly:
        return _biweekly_or_weekly_dates(
            bill.first_due_date,  # type: ignore[arg-type]
            timedelta(days=14),
            window_start,
            window_end,
        )

    if r == BillRecurrence.weekly:
        return _biweekly_or_weekly_dates(
            bill.first_due_date,  # type: ignore[arg-type]
            timedelta(days=7),
            window_start,
            window_end,
        )

    if r == BillRecurrence.quarterly:
        return _anchor_recurrence_dates(
            bill.first_due_date,  # type: ignore[arg-type]
            3,
            window_start,
            window_end,
        )

    if r == BillRecurrence.semiannual:
        return _anchor_recurrence_dates(
            bill.first_due_date,  # type: ignore[arg-type]
            6,
            window_start,
            window_end,
        )

    if r == BillRecurrence.annual:
        return _anchor_recurrence_dates(
            bill.first_due_date,  # type: ignore[arg-type]
            12,
            window_start,
            window_end,
        )

    if r == BillRecurrence.one_time:
        if window_start <= bill.first_due_date <= window_end:  # type: ignore[operator]
            return [bill.first_due_date]  # type: ignore[list-item]
        return []

    return []


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------


def _find_period(
    periods: list[PayPeriodResult], effective_due: date
) -> PayPeriodResult | None:
    """
    Return the last period whose period_start <= effective_due_date.
    Returns None when effective_due_date precedes all period starts (late-flagged).
    """
    result: PayPeriodResult | None = None
    for p in periods:
        if p.period_start <= effective_due:
            result = p
        else:
            break
    return result


def assign_bills(
    periods: list[PayPeriodResult],
    bills: list[BillInput],
) -> list[PayPeriodResult]:
    """
    Assign bill occurrences to pay periods.  Mutates and returns *periods*.

    Assignment rule: each bill due date is assigned to the last period whose
    period_start <= effective_due_date (due_date + grace_period_days).  Bills
    whose effective due date precedes all period starts are attached to the
    first period and marked late_flagged.
    """
    if not periods:
        return periods

    period_start = periods[0].period_start
    window_end = periods[-1].period_end

    for bill in bills:
        # For one-time bills look back 365 days to catch bills already past due.
        # Recurring bills are forward-projected from period_start only.
        gen_start = (
            period_start - timedelta(days=365)
            if bill.recurrence == BillRecurrence.one_time
            else period_start
        )
        for due_date in due_dates_for_bill(bill, gen_start, window_end):
            effective_due = due_date + timedelta(days=bill.grace_period_days)
            if effective_due > window_end:
                continue
            period = _find_period(periods, effective_due)

            if period is None:
                status = "late_flagged"
                period = periods[0]
            else:
                status = "on_time"

            period.assigned_bills.append(
                AssignedBill(
                    bill_id=bill.id,
                    name=bill.name,
                    due_date=due_date,
                    amount=bill.amount,
                    status=status,
                )
            )

    for p in periods:
        p.assigned_bills.sort(key=lambda b: b.due_date)

    return periods


# ---------------------------------------------------------------------------
# Top-level projection
# ---------------------------------------------------------------------------


def project(
    first_paycheck_date: date,
    frequency: PayFrequency,
    num_periods: int,
    net_salary: Decimal,
    beginning_balance: Decimal,
    bills: list[BillInput],
) -> list[PayPeriodResult]:
    """Generate periods, assign all bills, then apply rolling balances."""
    periods = build_periods(first_paycheck_date, frequency, num_periods)
    assign_bills(periods, bills)
    apply_rolling_balances(periods, net_salary, beginning_balance)
    return periods
