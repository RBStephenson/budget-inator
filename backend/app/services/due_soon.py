"""Bill digest selection for the daily digest (BI-75, BI-78).

Pure functions over the schedule engine's output: no database access, so the
selection rules are testable without a pay schedule or a clock.

The question the digest answers is "which paycheck pays which bill". Each
bill's **Pay on** date is the pay date of the period the engine assigned it
to, the same value the dashboard shows, so a bill that was moved, rebalanced
or paid early carries the paycheck it was actually put on.

Paid status is deliberately *not* a filter. Bills often go unmarked in the app
for weeks, so filtering on "unpaid" would list dozens of bills that are already
paid. Instead every selected bill is listed, and ones the app knows are paid
are tagged.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.models.enums import BillStatus
from app.schemas.schedule import AssignedBillOut, PayPeriodOut

DEFAULT_WINDOW_DAYS = 3
MAX_WINDOW_DAYS = 31


@dataclass(frozen=True)
class DueSoonItem:
    bill_id: int
    name: str
    due_date: date
    pay_on: date
    amount: Decimal
    is_variable: bool
    marked_paid: bool


@dataclass(frozen=True)
class DueSoonDigest:
    today: date
    window_end: date
    window_days: int
    is_payday: bool
    items: tuple[DueSoonItem, ...]
    unmarked_from_earlier: int = 0
    # Payday only: bills due in the short window that are paid from a
    # different paycheck, so a bill due tomorrow never hides inside a count.
    also_due: tuple[DueSoonItem, ...] = ()

    @property
    def total(self) -> Decimal:
        return sum((item.amount for item in self.items), Decimal("0"))


def _key(item: DueSoonItem) -> tuple[int, date]:
    return (item.bill_id, item.due_date)


def _sorted(items: list[DueSoonItem]) -> tuple[DueSoonItem, ...]:
    return tuple(sorted(items, key=lambda item: (item.due_date, item.name.lower())))


def _to_item(bill: AssignedBillOut, pay_on: date) -> DueSoonItem:
    return DueSoonItem(
        bill_id=bill.bill_id,
        name=bill.name,
        due_date=bill.due_date,
        pay_on=pay_on,
        amount=bill.actual_amount if bill.actual_amount is not None else bill.amount,
        is_variable=bill.is_variable,
        marked_paid=bill.status == BillStatus.paid,
    )


def _payday_items(period: PayPeriodOut) -> tuple[list[DueSoonItem], int]:
    """Bills assigned to this paycheck, plus a count of carried-in ones.

    Carried copies are bills from an earlier paycheck that aren't marked paid.
    They're counted, not listed: while bills go unmarked for weeks, listing
    them would bury the bills this paycheck actually pays.
    """
    items = [
        _to_item(bill, period.pay_date)
        for bill in period.assigned_bills
        if not bill.is_carried_over and bill.status != BillStatus.skipped
    ]
    carried = sum(
        1
        for bill in period.assigned_bills
        if bill.is_carried_over and bill.status != BillStatus.skipped
    )
    return items, carried


def _window_items(
    periods: Sequence[PayPeriodOut], today: date, window_end: date
) -> list[DueSoonItem]:
    """Bills due from ``today`` through ``window_end``, each listed once.

    A bill's own copy is preferred so its Pay on is the paycheck it was
    assigned to. A carried copy is only a fallback: past-due carries are
    already outside the window, and dropping in-window carries could hide a
    bill whose own copy isn't in the fetched periods.
    """
    candidates = [
        (bill, period.pay_date)
        for carried_pass in (False, True)
        for period in periods
        for bill in period.assigned_bills
        if bill.is_carried_over is carried_pass
    ]
    seen: set[tuple[int, date]] = set()
    items: list[DueSoonItem] = []
    for bill, pay_on in candidates:
        key = (bill.bill_id, bill.due_date)
        if (
            bill.status == BillStatus.skipped
            or not today <= bill.due_date <= window_end
            or key in seen
        ):
            continue
        seen.add(key)
        items.append(_to_item(bill, pay_on))
    return items


def select_due_soon(
    periods: Sequence[PayPeriodOut],
    today: date,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> DueSoonDigest:
    """Select the bills for today's digest.

    On a payday (today is some period's effective pay date, including one
    moved earlier than its period start) the list is exactly the bills
    assigned to that paycheck, whatever their due dates, plus a count of
    unmarked bills carried in from earlier paychecks. The short due-soon
    window still runs: anything due in it that's paid from a different
    paycheck is listed separately, so a bill due tomorrow can't vanish into
    the count.

    Any other day, it's the bills due from ``today`` through
    ``today + window_days``, inclusive, each with its Pay on paycheck.

    Skipped bills are always left out.
    """
    if not 0 <= window_days <= MAX_WINDOW_DAYS:
        raise ValueError(
            f"window_days must be between 0 and {MAX_WINDOW_DAYS}, got {window_days}"
        )

    short_window_end = today + timedelta(days=window_days)
    due_soon = _window_items(periods, today, short_window_end)
    payday_period = next((p for p in periods if p.pay_date == today), None)
    if payday_period is None:
        return DueSoonDigest(
            today=today,
            window_end=short_window_end,
            window_days=window_days,
            is_payday=False,
            items=_sorted(due_soon),
        )

    items, unmarked_from_earlier = _payday_items(payday_period)
    on_this_paycheck = {_key(item) for item in items}
    return DueSoonDigest(
        today=today,
        window_end=payday_period.period_end,
        window_days=window_days,
        is_payday=True,
        items=_sorted(items),
        unmarked_from_earlier=unmarked_from_earlier,
        also_due=_sorted(
            [item for item in due_soon if _key(item) not in on_this_paycheck]
        ),
    )


def _bills(count: int) -> str:
    return f"{count} bill" if count == 1 else f"{count} bills"


def _render_item(item: DueSoonItem, show_pay_on: bool) -> str:
    approx = "~" if item.is_variable else ""
    tags = []
    if show_pay_on:
        tags.append(f"pay on {item.pay_on:%a %b %d}")
    if item.marked_paid:
        tags.append("marked paid")
    suffix = f" ({', '.join(tags)})" if tags else ""
    return (
        f"- Due {item.due_date:%a %b %d}: {item.name}, "
        f"{approx}${item.amount:,.2f}{suffix}"
    )


def render_markdown(digest: DueSoonDigest) -> str:
    """Render the digest as a short markdown file.

    The first line is ``generated: YYYY-MM-DD`` so a reader can tell a stale
    file from today's.
    """
    lines = [
        f"generated: {digest.today.isoformat()}",
        "status: ok",
        "",
        "# Bills due",
        "",
    ]
    if digest.is_payday:
        lines.append(
            f"Payday ({digest.today:%a %b %d}): the bills to pay from today's "
            "paycheck, by due date."
        )
    else:
        lines.append(
            f"Due in the next {digest.window_days} days ({digest.today:%a %b %d} "
            f"to {digest.window_end:%a %b %d}), with the paycheck each is paid from."
        )
    lines.append("")

    if not digest.items:
        lines.append(
            "No bills assigned to this paycheck."
            if digest.is_payday
            else "No bills due in this window."
        )
    else:
        for item in digest.items:
            lines.append(_render_item(item, show_pay_on=not digest.is_payday))
        lines.append("")
        lines.append(f"Total: ${digest.total:,.2f} across {_bills(len(digest.items))}.")

    if digest.also_due:
        lines.append("")
        lines.append(
            f"Also due in the next {digest.window_days} days, paid from a "
            "different paycheck:"
        )
        for item in digest.also_due:
            lines.append(_render_item(item, show_pay_on=True))

    if digest.unmarked_from_earlier:
        verb = "isn't" if digest.unmarked_from_earlier == 1 else "aren't"
        lines.append("")
        lines.append(
            f"{_bills(digest.unmarked_from_earlier)} from earlier paychecks {verb} "
            "marked paid in Budget Inator."
        )

    lines.append("")
    lines.append(
        "Paid status comes from Budget Inator and is only as current as the last "
        "time bills were marked paid there."
    )
    return "\n".join(lines) + "\n"


def render_error(today: date, message: str) -> str:
    """Render a failure file, so a reader sees the error instead of an old list."""
    return (
        f"generated: {today.isoformat()}\n"
        "status: error\n"
        "\n"
        "# Bills due: digest FAILED\n"
        "\n"
        f"{message}\n"
    )
