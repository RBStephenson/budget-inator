from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

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
    due_day: int | None  # fixed month-day for monthly bills (1–31)
    first_due_date: date | None  # anchor date for non-monthly bills
    grace_period_days: int = 0
    due_day_is_month_end: bool = False
    category: str = "other"
    is_variable: bool = False
    sinking_fund_enabled: bool = False
    is_active: bool = True
    active_start: date | None = None
    active_end: date | None = None


@dataclass
class AssignedBill:
    bill_id: int
    name: str
    due_date: date
    amount: Decimal
    status: str  # "on_time" | "late_flagged"
    category: str = "other"
    is_variable: bool = False
    placement_source: str = "inferred"
    manual_pay_date: date | None = None
    sinking_fund_applied: Decimal = Decimal("0")
    sinking_fund_shortfall: Decimal = Decimal("0")
    actual_amount: Decimal | None = None
    skipped: bool = False


def assigned_bill_effective_amount(b: AssignedBill) -> Decimal:
    """Cash actually committed by *b*, matching schedule_service._to_period_out.

    A confirmed actual amount overrides the estimate; sinking-fund-covered
    bills draw from the shortfall (what's left after the reserve). This keeps
    the engine's rollover math and the API's displayed remaining balance from
    silently diverging when a bill is paid off-estimate or skipped.
    """
    if b.actual_amount is not None:
        if b.sinking_fund_applied > 0:
            return max(Decimal("0"), b.actual_amount - b.sinking_fund_applied)
        return b.actual_amount
    if b.sinking_fund_applied > 0 or b.sinking_fund_shortfall > 0:
        return b.sinking_fund_shortfall
    return b.amount


@dataclass
class SinkingFundContribution:
    bill_id: int
    name: str
    next_due_date: date
    target_amount: Decimal
    saved_amount: Decimal
    contribution_amount: Decimal
    shortfall_amount: Decimal
    surplus_amount: Decimal


@dataclass
class PayPeriodResult:
    period_index: int
    pay_date: date
    period_start: date
    period_end: date
    opening_balance: Decimal
    assigned_bills: list[AssignedBill] = field(default_factory=list)
    sinking_fund_contributions: list[SinkingFundContribution] = field(
        default_factory=list
    )

    @property
    def remaining_balance(self) -> Decimal:
        bill_total = sum(
            assigned_bill_effective_amount(b)
            for b in self.assigned_bills
            if not b.skipped
        )
        contribution_total = sum(
            c.contribution_amount for c in self.sinking_fund_contributions
        )
        return self.opening_balance - bill_total - contribution_total


@dataclass
class ActualAnchor:
    """Confirmed payday actuals for a single pay date (see #55).

    ``actual_balance`` is the real post-deposit account balance; when present it
    re-anchors the period's opening balance. ``actual_net_pay`` overrides the
    assumed salary for that period only.
    """

    actual_net_pay: Decimal | None = None
    actual_balance: Decimal | None = None


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


def _next_pay_date(
    current: date,
    frequency: PayFrequency,
    *,
    semimonthly_month_end: bool = False,
) -> date:
    if frequency == PayFrequency.weekly:
        return current + timedelta(days=7)
    if frequency == PayFrequency.biweekly:
        return current + timedelta(days=14)
    if frequency == PayFrequency.semimonthly:
        if semimonthly_month_end:
            # 15th → month-end; month-end → 15th of the next month.
            if current.day <= 15:
                return current.replace(day=_days_in_month(current.year, current.month))
            next_month = _add_months(current.replace(day=1), 1)
            return next_month.replace(day=15)
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
    # A semimonthly anchor after the 15th represents the common
    # 15th/month-end schedule. Derive this once from the original anchor so the
    # pattern is not lost when subsequent generated dates land on the 15th.
    semimonthly_month_end = (
        frequency == PayFrequency.semimonthly and first_paycheck_date.day > 15
    )

    # Need num_periods + 1 pay dates to know each period's end date.
    if frequency == PayFrequency.monthly:
        # Derive each date from the original anchor (not the previous one) so a
        # short month clamping the day (e.g. Jan 31 -> Feb 29) doesn't drag every
        # later date down with it.
        pay_dates: list[date] = [
            _add_months(first_paycheck_date, i) for i in range(num_periods + 1)
        ]
    else:
        pay_dates = [first_paycheck_date]
        for _ in range(num_periods):
            pay_dates.append(
                _next_pay_date(
                    pay_dates[-1],
                    frequency,
                    semimonthly_month_end=semimonthly_month_end,
                )
            )

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
    actuals: dict[date, ActualAnchor] | None = None,
) -> None:
    """
    Set opening_balance on each period using rolling carry-over.

    Period 0 opens with beginning_balance + net_salary.
    Each subsequent period opens with previous remaining_balance + net_salary.
    Must be called AFTER bills are assigned so remaining_balance is accurate.

    Confirmed payday actuals (#55) override the computed values:
    - ``actual_balance`` is the real post-deposit balance, so it becomes the
      period's opening balance directly and everything after rolls forward from
      there (the deposit is already reflected, so net pay is not re-added).
    - otherwise ``actual_net_pay`` replaces the assumed salary for that period.
    """
    actuals = actuals or {}
    for i, p in enumerate(periods):
        anchor = actuals.get(p.pay_date)
        if anchor is not None and anchor.actual_balance is not None:
            p.opening_balance = anchor.actual_balance
            continue
        income = (
            anchor.actual_net_pay
            if anchor is not None and anchor.actual_net_pay is not None
            else net_salary
        )
        if i == 0:
            p.opening_balance = beginning_balance + income
        else:
            p.opening_balance = periods[i - 1].remaining_balance + income


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
    """All occurrences of anchor + k*months in [window_start, window_end].

    Each occurrence is derived from *anchor* directly (not the previous
    occurrence) so a short month clamping the day (e.g. Jan 31 -> Feb 29)
    doesn't drag every later occurrence down with it.
    """
    k = 0
    d = anchor
    # Walk forward to first occurrence >= window_start
    while d < window_start:
        k += 1
        d = _add_months(anchor, k * months)
    dates = []
    while d <= window_end:
        dates.append(d)
        k += 1
        d = _add_months(anchor, k * months)
    return dates


def due_dates_for_bill(
    bill: BillInput, window_start: date, window_end: date
) -> list[date]:
    """All due dates for *bill* that fall within [window_start, window_end]."""
    if not bill.is_active:
        return []
    if bill.active_start is not None:
        window_start = max(window_start, bill.active_start)
    if bill.active_end is not None:
        window_end = min(window_end, bill.active_end)
    if window_start > window_end:
        return []

    r = bill.recurrence

    if r == BillRecurrence.monthly:
        assert bill.due_day is not None or bill.due_day_is_month_end
        due_day = bill.due_day

        def month_day(year: int, month: int) -> int:
            last_day = _days_in_month(year, month)
            if bill.due_day_is_month_end:
                return last_day
            assert due_day is not None
            return min(due_day, last_day)

        dates: list[date] = []
        # First candidate: due_day in window_start's month, clamped to actual days
        d = date(
            window_start.year,
            window_start.month,
            month_day(window_start.year, window_start.month),
        )
        if d < window_start:
            d = _add_months(d, 1)
            d = d.replace(day=month_day(d.year, d.month))
        while d <= window_end:
            dates.append(d)
            d = _add_months(d, 1)
            d = d.replace(day=month_day(d.year, d.month))
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


def _find_period_containing(
    periods: list[PayPeriodResult], when: date
) -> PayPeriodResult | None:
    """Return the period whose [period_start, period_end] contains *when*."""
    for p in periods:
        if p.period_start <= when <= p.period_end:
            return p
    return None


def assign_bills(
    periods: list[PayPeriodResult],
    bills: list[BillInput],
    paid_dates: dict[tuple[int, date], date] | None = None,
    manual_pay_dates: dict[tuple[int, date], date] | None = None,
    actual_amounts: dict[tuple[int, date], Decimal] | None = None,
    skipped_dates: set[tuple[int, date]] | None = None,
) -> list[PayPeriodResult]:
    """
    Assign bill occurrences to pay periods.  Mutates and returns *periods*.

    Assignment rule: each bill due date is assigned to the period containing
    it. A grace period does not shift this default placement — it only
    widens the set of periods ``rebalance_grace_period_bills`` may move the
    occurrence into later, and only when the due-date period can't cover it.
    Bills whose due date precedes every period fall back to the period
    containing the grace-extended effective due date (due_date +
    grace_period_days), rescuing an already-overdue bill from being
    late_flagged when its grace window reaches into the schedule; if even
    that fails, they're attached to the first period and marked
    late_flagged.

    *paid_dates* maps ``(bill_id, due_date)`` to the date a bill was actually
    paid.  A paid occurrence is assigned to the period containing its paid date
    instead of its due-date period, so the spend lands where the cash left the
    account (e.g. a bill paid early moves from a future period into the current
    one).  Falls back to the due-date rule when the paid date lands outside the
    generated periods.

    *actual_amounts* maps ``(bill_id, due_date)`` to a confirmed actual amount,
    and *skipped_dates* is the set of ``(bill_id, due_date)`` occurrences marked
    skipped. Both feed ``PayPeriodResult.remaining_balance``, so a recorded
    actual amount or skip is reflected in the balance rolled into every later
    period, not just the one it was recorded in.
    """
    if not periods:
        return periods

    paid_dates = paid_dates or {}
    manual_pay_dates = manual_pay_dates or {}
    actual_amounts = actual_amounts or {}
    skipped_dates = skipped_dates or set()
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
            paid_on = paid_dates.get((bill.id, due_date))
            manual_pay_date = manual_pay_dates.get((bill.id, due_date))
            paid_period = (
                _find_period_containing(periods, paid_on)
                if paid_on is not None
                else None
            )
            manual_period = (
                _find_period_containing(periods, manual_pay_date)
                if manual_pay_date is not None
                else None
            )
            period: PayPeriodResult
            placement_source = "inferred"
            if paid_period is not None:
                # Relocate the paid bill to the period it was actually paid in.
                period = paid_period
                status = "on_time"
                placement_source = "paid"
            elif manual_period is not None:
                period = manual_period
                status = "on_time"
                placement_source = "manual"
            else:
                due_period = _find_period_containing(periods, due_date)
                if due_period is not None:
                    status = "on_time"
                    period = due_period
                else:
                    # due_date precedes every period; see if the grace
                    # window reaches far enough to place it normally anyway.
                    rescue_period = _find_period(periods, effective_due)
                    if rescue_period is None:
                        status = "late_flagged"
                        period = periods[0]
                    else:
                        status = "on_time"
                        period = rescue_period

            period.assigned_bills.append(
                AssignedBill(
                    bill_id=bill.id,
                    name=bill.name,
                    due_date=due_date,
                    amount=bill.amount,
                    status=status,
                    category=bill.category,
                    is_variable=bill.is_variable,
                    placement_source=placement_source,
                    manual_pay_date=manual_pay_date,
                    actual_amount=actual_amounts.get((bill.id, due_date)),
                    skipped=(bill.id, due_date) in skipped_dates,
                )
            )

    for p in periods:
        p.assigned_bills.sort(key=lambda b: b.due_date)

    return periods


def _period_indexes_for_payment_window(
    periods: list[PayPeriodResult], due_date: date, grace_period_days: int
) -> list[int]:
    """Return period indexes where a bill can be paid without exceeding grace."""
    effective_due = due_date + timedelta(days=grace_period_days)
    return [
        index
        for index, period in enumerate(periods)
        if period.period_end >= due_date and period.period_start <= effective_due
    ]


def _rebalance_score(periods: list[PayPeriodResult]) -> tuple[int, Decimal, Decimal]:
    deficits = [
        -period.remaining_balance
        for period in periods
        if period.remaining_balance < Decimal("0")
    ]
    if not deficits:
        return (0, Decimal("0"), Decimal("0"))
    return (len(deficits), sum(deficits, Decimal("0")), max(deficits))


def _bill_version_for_due_date(
    versions: list[BillInput] | None, due_date: date
) -> BillInput | None:
    """Pick the version whose active window covers *due_date*.

    ``bills`` can contain multiple entries sharing an id when a bill's terms
    changed mid-schedule (see ``bill_versions.bill_inputs_for_window``), each
    scoped to an ``active_start``/``active_end`` window. Falls back to the
    last version if none matches (versions with no active window set).
    """
    if not versions:
        return None
    for version in versions:
        if version.active_start is not None and version.active_start > due_date:
            continue
        if version.active_end is not None and version.active_end < due_date:
            continue
        return version
    return versions[-1]


def _move_assigned_bill(
    periods: list[PayPeriodResult],
    bill: AssignedBill,
    from_index: int,
    to_index: int,
) -> None:
    periods[from_index].assigned_bills.remove(bill)
    periods[to_index].assigned_bills.append(bill)


def rebalance_grace_period_bills(
    periods: list[PayPeriodResult],
    bills: list[BillInput],
    net_salary: Decimal,
    beginning_balance: Decimal,
    actuals: dict[date, ActualAnchor] | None = None,
    paid_dates: dict[tuple[int, date], date] | None = None,
    manual_pay_dates: dict[tuple[int, date], date] | None = None,
) -> None:
    """Move unpaid bills within grace windows to reduce projected overdrafts.

    Grace periods create payment flexibility: a bill can be carried by any pay
    period that overlaps its due-date-through-grace window.  The first
    assignment pass intentionally keeps the simple due-date rule; this pass then
    tries alternate valid placements and keeps only moves that improve the
    projected negative balances across the generated schedule.
    """
    if not periods:
        return

    paid_dates = paid_dates or {}
    manual_pay_dates = manual_pay_dates or {}
    bills_by_id: dict[int, list[BillInput]] = {}
    for input_bill in bills:
        bills_by_id.setdefault(input_bill.id, []).append(input_bill)
    apply_rolling_balances(periods, net_salary, beginning_balance, actuals)

    movable: list[tuple[AssignedBill, list[int]]] = []
    for period_index, period in enumerate(periods):
        for assigned in period.assigned_bills:
            bill = _bill_version_for_due_date(
                bills_by_id.get(assigned.bill_id), assigned.due_date
            )
            if bill is None:
                continue
            if paid_dates.get((assigned.bill_id, assigned.due_date)) is not None:
                continue
            if manual_pay_dates.get((assigned.bill_id, assigned.due_date)) is not None:
                continue
            candidate_indexes = _period_indexes_for_payment_window(
                periods, assigned.due_date, bill.grace_period_days
            )
            if len(candidate_indexes) <= 1 or period_index not in candidate_indexes:
                continue
            movable.append((assigned, candidate_indexes))

    if not movable:
        return

    # Each accepted move improves the score, so the loop naturally converges.
    for _ in range(len(movable) * max(1, len(periods))):
        current_score = _rebalance_score(periods)
        if current_score[0] == 0:
            break

        best_move: tuple[AssignedBill, int, int] | None = None
        best_score = current_score

        for assigned, candidate_indexes in movable:
            current_index = next(
                (
                    index
                    for index, period in enumerate(periods)
                    if assigned in period.assigned_bills
                ),
                None,
            )
            if current_index is None:
                continue

            for candidate_index in candidate_indexes:
                if candidate_index == current_index:
                    continue
                _move_assigned_bill(periods, assigned, current_index, candidate_index)
                apply_rolling_balances(periods, net_salary, beginning_balance, actuals)
                score = _rebalance_score(periods)
                _move_assigned_bill(periods, assigned, candidate_index, current_index)
                apply_rolling_balances(periods, net_salary, beginning_balance, actuals)
                if score < best_score:
                    best_score = score
                    best_move = (assigned, current_index, candidate_index)

        if best_move is None:
            break

        assigned, from_index, to_index = best_move
        _move_assigned_bill(periods, assigned, from_index, to_index)
        apply_rolling_balances(periods, net_salary, beginning_balance, actuals)

    for period in periods:
        period.assigned_bills.sort(key=lambda bill: bill.due_date)


def _effective_assigned_amount(bill: AssignedBill) -> Decimal:
    if bill.sinking_fund_applied > 0 or bill.sinking_fund_shortfall > 0:
        return bill.sinking_fund_shortfall
    return bill.amount


def apply_sinking_funds(periods: list[PayPeriodResult], bills: list[BillInput]) -> None:
    """Project sinking-fund contributions and due-date reserve use.

    This is intentionally projection-only: the app does not persist bank transfer
    transactions yet. Contributions reserve money by reducing available cash in
    each period, and the reserve is applied to the next due occurrence when it
    appears in the generated schedule.
    """
    if not periods:
        return

    sinking_bills = [b for b in bills if b.sinking_fund_enabled and b.is_active]
    if not sinking_bills:
        return

    reserves: dict[int, Decimal] = {b.id: Decimal("0") for b in sinking_bills}
    window_start = periods[0].period_start
    window_end = periods[-1].period_end
    sinking_lookahead_end = window_end + timedelta(days=370)
    due_dates_by_bill = {
        b.id: due_dates_for_bill(b, window_start, sinking_lookahead_end)
        for b in sinking_bills
    }

    for index, period in enumerate(periods):
        # First consume reserve for due occurrences in this period.
        for assigned in period.assigned_bills:
            if assigned.bill_id not in reserves or assigned.skipped:
                continue
            due_amount = (
                assigned.actual_amount
                if assigned.actual_amount is not None
                else assigned.amount
            )
            reserve = reserves[assigned.bill_id]
            applied = min(reserve, due_amount)
            assigned.sinking_fund_applied = applied
            assigned.sinking_fund_shortfall = max(Decimal("0"), due_amount - applied)
            reserves[assigned.bill_id] = max(Decimal("0"), reserve - due_amount)

        for bill in sinking_bills:
            future_due_dates = [
                d for d in due_dates_by_bill[bill.id] if d > period.period_end
            ]
            if not future_due_dates:
                continue
            next_due = future_due_dates[0]
            funding_period_count = sum(
                1 for p in periods[index:] if p.period_end < next_due
            )
            if funding_period_count <= 0:
                continue

            reserve = reserves[bill.id]
            needed = max(Decimal("0"), bill.amount - reserve)
            # Quantize immediately: needed/funding_period_count can produce a
            # repeating decimal, and every downstream field (saved_amount,
            # shortfall_amount, surplus_amount, and every later period's
            # reserve) is a +/- of this value, so leaving it unquantized would
            # carry the imprecision through the whole projection.
            contribution = (needed / funding_period_count).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            reserves[bill.id] = reserve + contribution
            saved = reserves[bill.id]
            period.sinking_fund_contributions.append(
                SinkingFundContribution(
                    bill_id=bill.id,
                    name=bill.name,
                    next_due_date=next_due,
                    target_amount=bill.amount,
                    saved_amount=saved,
                    contribution_amount=contribution,
                    shortfall_amount=max(Decimal("0"), bill.amount - saved),
                    surplus_amount=max(Decimal("0"), saved - bill.amount),
                )
            )


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
    actuals: dict[date, ActualAnchor] | None = None,
    paid_dates: dict[tuple[int, date], date] | None = None,
    manual_pay_dates: dict[tuple[int, date], date] | None = None,
    actual_amounts: dict[tuple[int, date], Decimal] | None = None,
    skipped_dates: set[tuple[int, date]] | None = None,
) -> list[PayPeriodResult]:
    """Generate periods, assign all bills, then apply rolling balances."""
    periods = build_periods(first_paycheck_date, frequency, num_periods)
    assign_bills(
        periods, bills, paid_dates, manual_pay_dates, actual_amounts, skipped_dates
    )
    rebalance_grace_period_bills(
        periods,
        bills,
        net_salary,
        beginning_balance,
        actuals,
        paid_dates,
        manual_pay_dates,
    )
    apply_sinking_funds(periods, bills)
    apply_rolling_balances(periods, net_salary, beginning_balance, actuals)
    return periods
