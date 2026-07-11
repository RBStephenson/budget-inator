"""Pay-period projection and monthly-summary builders.

Pure data services shared by the schedule API and the PDF report. Kept out of
the API layer so other services (e.g. the report) can reuse them without
importing route handlers.
"""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Bill, BillInstance, PaySchedule
from app.models.enums import BillStatus, PayFrequency
from app.models.pay_period_actual import PayPeriodActual
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
    RebalanceApplyRequest,
    RebalanceMove,
    RebalancePreviewRequest,
    RebalancePreviewResponse,
    ScheduleResponse,
    ScheduleSummary,
    SinkingFundContributionOut,
)
from app.services.bill_versions import bill_input_for_due_date, bill_inputs_for_window
from app.services.pay_period_engine import (
    ActualAnchor,
    BillInput,
    PayPeriodResult,
    build_periods,
    due_dates_for_bill,
    project,
)
from app.utils import utcnow

# Keyed by (bill_id, due_date)
_InstanceMap = dict[tuple[int, date], BillInstance]
# Keyed by original (computed) pay_date → overridden pay_date
_OverrideMap = dict[date, date]
# Keyed by pay_date → confirmed payday actuals (#55)
_ActualsMap = dict[date, ActualAnchor]
_PaidDatesMap = dict[tuple[int, date], date]
_ManualPayDateMap = dict[tuple[int, date], date]


def _load_paid_dates(db: Session) -> _PaidDatesMap:
    """Paid date per instance, keyed by (bill_id, due_date) (see relocation).

    Loaded in full (not windowed) because a bill paid early can belong to a
    later period than its due date, and one paid late to an earlier one, so the
    relocation must be visible regardless of which window is requested.
    """
    rows = (
        db.query(BillInstance)
        .filter(
            BillInstance.status == BillStatus.paid,
            BillInstance.paid_at.isnot(None),
        )
        .all()
    )
    return {
        (r.bill_id, r.due_date): r.paid_at.date() for r in rows if r.paid_at is not None
    }


def _load_manual_pay_dates(db: Session) -> _ManualPayDateMap:
    rows = (
        db.query(BillInstance)
        .filter(
            BillInstance.manual_pay_date.isnot(None),
            BillInstance.status.notin_([BillStatus.paid, BillStatus.skipped]),
        )
        .all()
    )
    return {
        (r.bill_id, r.due_date): r.manual_pay_date
        for r in rows
        if r.manual_pay_date is not None
    }


def _load_actuals(db: Session) -> _ActualsMap:
    """All confirmed payday actuals, keyed by pay date (see #55).

    Loaded in full (not windowed) because an actual balance on a past payday
    re-anchors every period after it, including those in the current window.
    """
    return {
        row.pay_date: ActualAnchor(
            actual_net_pay=row.actual_net_pay,
            actual_balance=row.actual_balance,
        )
        for row in db.query(PayPeriodActual).all()
    }


_MIN_PERIOD_DAYS: dict[PayFrequency, int] = {
    PayFrequency.weekly: 7,
    PayFrequency.biweekly: 14,
    PayFrequency.semimonthly: 13,
    PayFrequency.monthly: 28,
}

_CATEGORY_ORDER = [
    "housing",
    "utilities",
    "subscriptions",
    "insurance",
    "debt",
    "savings",
    "other",
]

MAX_SCHEDULE_RANGE_DAYS = 730
MAX_MONTHLY_SUMMARY_MONTHS = 36
MAX_PROJECTED_PERIODS = 5000


def _periods_needed(first_paycheck: date, target: date, frequency: PayFrequency) -> int:
    """Conservative upper bound on periods needed to reach *target*."""
    delta = max(0, (target - first_paycheck).days)
    return delta // _MIN_PERIOD_DAYS[frequency] + 5


def _ensure_schedule_range_allowed(from_date: date, to_date: date) -> None:
    if (to_date - from_date).days > MAX_SCHEDULE_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"date range must be {MAX_SCHEDULE_RANGE_DAYS} days or less",
        )


def _ensure_projected_periods_allowed(num_needed: int) -> None:
    if num_needed > MAX_PROJECTED_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"schedule projection is limited to {MAX_PROJECTED_PERIODS} periods",
        )


def _month_span(from_year: int, from_month: int, to_year: int, to_month: int) -> int:
    return (to_year - from_year) * 12 + (to_month - from_month) + 1


def _find_current_index(periods: list[PayPeriodResult], today: date) -> int:
    """Index of the period containing *today*, or the first future period."""
    for i, p in enumerate(periods):
        if p.period_start <= today <= p.period_end:
            return i
        if p.period_start > today:
            return i
    return max(0, len(periods) - 1)


def _to_period_out(
    p: PayPeriodResult,
    instances: _InstanceMap,
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
                is_variable=b.is_variable,
                category=b.category,
                placement_source=b.placement_source,
                manual_pay_date=b.manual_pay_date,
                sinking_fund_applied=b.sinking_fund_applied,
                sinking_fund_shortfall=b.sinking_fund_shortfall,
            )
        )

    def _effective_amount(bo: AssignedBillOut) -> Decimal:
        if bo.actual_amount is not None:
            actual = Decimal(str(bo.actual_amount))
            if bo.sinking_fund_applied > 0:
                return max(Decimal("0"), actual - bo.sinking_fund_applied)
            return actual
        if bo.sinking_fund_applied > 0 or bo.sinking_fund_shortfall > 0:
            return Decimal(str(bo.sinking_fund_shortfall))
        return bo.amount

    total = sum(
        (
            _effective_amount(bo)
            for bo in bills_out
            if bo.status != BillStatus.skipped and not bo.is_carried_over
        ),
        Decimal("0"),
    )
    total_sinking_funds = sum(
        (c.contribution_amount for c in p.sinking_fund_contributions),
        Decimal("0"),
    )
    remaining = p.opening_balance - total - total_sinking_funds
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
        total_sinking_funds=total_sinking_funds,
        remaining_balance=remaining,
        flagged_bill_count=flagged,
        assigned_bills=bills_out,
        sinking_fund_contributions=[
            SinkingFundContributionOut(
                bill_id=c.bill_id,
                name=c.name,
                next_due_date=c.next_due_date,
                target_amount=c.target_amount,
                saved_amount=c.saved_amount,
                contribution_amount=c.contribution_amount,
                shortfall_amount=c.shortfall_amount,
                surplus_amount=c.surplus_amount,
            )
            for c in p.sinking_fund_contributions
        ],
    )


def _add_carried_unpaid_bills(
    periods: list[PayPeriodOut],
    carry_target_index: int,
) -> None:
    carried: dict[tuple[int, date], AssignedBillOut] = {}

    for period in periods:
        current_bills = list(period.assigned_bills)
        current_keys = {(bill.bill_id, bill.due_date) for bill in current_bills}
        if period.period_index == carry_target_index:
            carry_ins = [
                bill.model_copy(update={"is_carried_over": True})
                for key, bill in carried.items()
                if key not in current_keys
            ]
            period.assigned_bills = sorted(
                [*current_bills, *carry_ins],
                key=lambda bill: (bill.due_date, bill.name.lower(), bill.bill_id),
            )
            period.flagged_bill_count = sum(
                1 for bill in period.assigned_bills if bill.status == "late_flagged"
            )

        next_carried: dict[tuple[int, date], AssignedBillOut] = {}
        for bill in period.assigned_bills:
            key = (bill.bill_id, bill.due_date)
            if bill.status in (BillStatus.paid, BillStatus.skipped):
                continue
            if bill.placement_source == "paid":
                continue
            next_carried[key] = bill.model_copy(update={"is_carried_over": True})
        carried = next_carried


def build_schedule(
    db: Session,
    from_date: date | None = None,
    to_date: date | None = None,
    default_count: int = 4,
) -> ScheduleResponse:
    """Project the pay-period schedule.

    When no date range is given, returns the current period plus
    ``default_count - 1`` upcoming periods. Shared by the schedule API and the
    PDF report service.
    """
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

    bill_rows = db.query(Bill).all()
    actuals = _load_actuals(db)
    paid_dates = _load_paid_dates(db)
    manual_pay_dates = _load_manual_pay_dates(db)

    today = date.today()

    if from_date is None and to_date is None:
        # Generate enough periods to find today + (default_count - 1) more
        num_needed = _periods_needed(first_paycheck, today, frequency) + default_count
        projection_end = build_periods(first_paycheck, frequency, num_needed)[
            -1
        ].period_end
        bills = bill_inputs_for_window(
            db, bill_rows, first_paycheck - timedelta(days=365), projection_end
        )
        all_periods = project(
            first_paycheck,
            frequency,
            num_needed,
            net_salary,
            beginning_balance,
            bills,
            actuals,
            paid_dates,
            manual_pay_dates,
        )
        current_idx = _find_current_index(all_periods, today)
        window = all_periods[current_idx : current_idx + default_count]
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
        _ensure_schedule_range_allowed(from_date, to_date)

        num_needed = _periods_needed(first_paycheck, to_date, frequency)
        _ensure_projected_periods_allowed(num_needed)
        projection_end = build_periods(first_paycheck, frequency, num_needed)[
            -1
        ].period_end
        bills = bill_inputs_for_window(
            db, bill_rows, first_paycheck - timedelta(days=365), projection_end
        )
        all_periods = project(
            first_paycheck,
            frequency,
            num_needed,
            net_salary,
            beginning_balance,
            bills,
            actuals,
            paid_dates,
            manual_pay_dates,
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
        window_end = window[-1].period_end
        carry_start = window[0].period_start - timedelta(days=365)
        carry_periods = [
            p
            for p in all_periods
            if p.period_end >= carry_start and p.period_start <= window_end
        ]
        # Past-due bills are pulled forward into the current period, so an
        # assigned bill's due date can precede the window's first period_start
        # (see assign_bills' 365-day look-back). Anchor the overlay query to the
        # earliest assigned due date, not period_start, or paid/skipped records
        # for those past-due bills get dropped and the bill renders as unpaid.
        assigned_due_dates = [
            b.due_date for p in carry_periods for b in p.assigned_bills
        ]
        instance_lower_bound = min([window[0].period_start, *assigned_due_dates])
        rows = (
            db.query(BillInstance)
            .filter(
                BillInstance.due_date >= instance_lower_bound,
                BillInstance.due_date <= window_end,
            )
            .all()
        )
        instances = {(r.bill_id, r.due_date): r for r in rows}

        pay_dates = [p.pay_date for p in carry_periods]
        override_rows = (
            db.query(PayPeriodOverride)
            .filter(PayPeriodOverride.original_pay_date.in_(pay_dates))
            .all()
        )
        override_map = {
            r.original_pay_date: r.overridden_pay_date for r in override_rows
        }

    if window:
        carry_start = window[0].period_start - timedelta(days=365)
        carry_periods = [
            p
            for p in all_periods
            if p.period_end >= carry_start and p.period_start <= window[-1].period_end
        ]
        carry_period_outs = [
            _to_period_out(p, instances, override_map) for p in carry_periods
        ]
        carry_target_index = _find_current_index(all_periods, today)
        _add_carried_unpaid_bills(carry_period_outs, carry_target_index)
        window_indexes = {p.period_index for p in window}
        period_outs = [p for p in carry_period_outs if p.period_index in window_indexes]
    else:
        period_outs = []

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


def build_rebalance_preview(
    db: Session,
    body: RebalancePreviewRequest,
) -> RebalancePreviewResponse:
    schedule = build_schedule(db, default_count=8)
    source_index = next(
        (
            index
            for index, period in enumerate(schedule.periods)
            if period.original_pay_date == body.source_pay_date
            or period.pay_date == body.source_pay_date
        ),
        None,
    )
    if source_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source pay period not found in the current schedule window",
        )

    source_period = schedule.periods[source_index]
    source_remaining = Decimal(str(source_period.remaining_balance))
    source_start = source_remaining
    moves: list[RebalanceMove] = []

    if source_remaining <= 0:
        return RebalancePreviewResponse(
            source_pay_date=source_period.original_pay_date,
            source_remaining_before=source_start,
            source_remaining_after=source_remaining,
            moves=[],
        )

    future_periods = [
        period
        for period in schedule.periods[source_index + 1 :]
        if Decimal(str(period.remaining_balance)) < 0
    ]

    for period in future_periods:
        future_remaining = Decimal(str(period.remaining_balance))
        candidates = sorted(
            (
                bill
                for bill in period.assigned_bills
                if bill.status == "on_time"
                and bill.placement_source == "inferred"
                and bill.sinking_fund_applied == 0
                and bill.sinking_fund_shortfall == 0
            ),
            key=lambda bill: (bill.due_date, Decimal(str(bill.amount))),
        )

        for bill in candidates:
            amount = (
                Decimal(str(bill.actual_amount))
                if bill.actual_amount is not None
                else Decimal(str(bill.amount))
            )
            if amount <= 0 or source_remaining - amount < 0:
                continue

            before_source = source_remaining
            before_future = future_remaining
            source_remaining -= amount
            future_remaining += amount
            moves.append(
                RebalanceMove(
                    bill_id=bill.bill_id,
                    name=bill.name,
                    due_date=bill.due_date,
                    amount=amount,
                    from_pay_date=period.original_pay_date,
                    to_pay_date=source_period.original_pay_date,
                    from_period_remaining_before=before_future,
                    from_period_remaining_after=future_remaining,
                    source_remaining_before=before_source,
                    source_remaining_after=source_remaining,
                    reason=(
                        f"{bill.name} is due {bill.due_date.isoformat()} and can "
                        f"be paid from the {source_period.pay_date.isoformat()} "
                        "paycheck because funds are available."
                    ),
                )
            )
            if len(moves) >= body.max_moves:
                break
            if future_remaining >= 0:
                break

        if len(moves) >= body.max_moves or source_remaining <= 0:
            break

    return RebalancePreviewResponse(
        source_pay_date=source_period.original_pay_date,
        source_remaining_before=source_start,
        source_remaining_after=source_remaining,
        moves=moves,
    )


def apply_rebalance_moves(db: Session, body: RebalanceApplyRequest) -> None:
    now = utcnow()
    for move in body.moves:
        bill = db.get(Bill, move.bill_id)
        if bill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bill {move.bill_id} not found",
            )

        inst = (
            db.query(BillInstance)
            .filter(
                BillInstance.bill_id == move.bill_id,
                BillInstance.due_date == move.due_date,
            )
            .first()
        )
        if inst is not None and inst.status in (BillStatus.paid, BillStatus.skipped):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="paid or skipped bills cannot be manually rebalanced",
            )

        if inst is None:
            bill_terms = bill_input_for_due_date(db, bill, move.due_date)
            inst = BillInstance(
                bill_id=move.bill_id,
                due_date=move.due_date,
                estimated_amount=bill_terms.amount,
                status=BillStatus.pending,
                manual_pay_date=move.to_pay_date,
                created_at=now,
                updated_at=now,
            )
            db.add(inst)
        else:
            inst.manual_pay_date = move.to_pay_date
            inst.updated_at = now

    db.commit()


# ---------------------------------------------------------------------------
# Monthly summary
# ---------------------------------------------------------------------------


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


def build_monthly_summary(
    db: Session,
    from_month: str | None = None,
    to_month: str | None = None,
) -> MonthlySummaryResponse:
    """Aggregate income, bills, and per-category subtotals by calendar month."""
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
    if _month_span(from_year, from_m, to_year, to_m) > MAX_MONTHLY_SUMMARY_MONTHS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"monthly summary range must be {MAX_MONTHLY_SUMMARY_MONTHS} "
                "months or less"
            ),
        )

    window_start = date(from_year, from_m, 1)
    window_end = _month_last_day(to_year, to_m)

    frequency = PayFrequency(sched.frequency)
    first_paycheck = sched.first_paycheck_date
    net_salary = Decimal(str(sched.net_salary))
    beginning_balance = Decimal(str(sched.beginning_balance))

    # Income per month: count pay periods whose period_start falls in the
    # window. Confirmed actual net pay (#55) overrides the assumed salary for
    # its own payday so the monthly view agrees with the pay-period view.
    actuals = _load_actuals(db)
    num_needed = _periods_needed(first_paycheck, window_end, frequency)
    _ensure_projected_periods_allowed(num_needed)
    all_pay_periods = build_periods(first_paycheck, frequency, num_needed)
    income_by_month: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    for p in all_pay_periods:
        if window_start <= p.period_start <= window_end:
            key = (p.period_start.year, p.period_start.month)
            anchor = actuals.get(p.pay_date)
            income = (
                anchor.actual_net_pay
                if anchor is not None and anchor.actual_net_pay is not None
                else net_salary
            )
            income_by_month[key] += income

    bill_rows = db.query(Bill).all()
    bill_inputs = bill_inputs_for_window(db, bill_rows, window_start, window_end)

    projected_periods = project(
        first_paycheck,
        frequency,
        num_needed,
        net_salary,
        beginning_balance,
        bill_inputs,
        actuals,
        _load_paid_dates(db),
        _load_manual_pay_dates(db),
    )
    sinking_by_month: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    for p in projected_periods:
        if window_start <= p.period_start <= window_end:
            key = (p.period_start.year, p.period_start.month)
            sinking_by_month[key] += sum(
                (c.contribution_amount for c in p.sinking_fund_contributions),
                Decimal("0"),
            )

    # Bills per month: find all due dates in the window
    bills_by_month: dict[tuple[int, int], list[tuple[BillInput, date]]] = defaultdict(
        list
    )
    for bill_input in bill_inputs:
        for due_date in due_dates_for_bill(bill_input, window_start, window_end):
            key = (due_date.year, due_date.month)
            bills_by_month[key].append((bill_input, due_date))

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

    def _build_item(bill: BillInput, due_date: date) -> MonthlyBillItem:
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
            amount=bill.amount,
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
        total_sinking_funds = sinking_by_month.get(key, Decimal("0"))
        available = total_income - total_bills - total_sinking_funds

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
                total_sinking_funds=total_sinking_funds,
                available=available,
                categories=categories,
            )
        )

    return MonthlySummaryResponse(months=result)
