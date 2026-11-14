"""Due-soon bill selection for the daily digest (BI-75).

Pure functions over the schedule engine's output: no database access, so the
selection rules are testable without a pay schedule or a clock.

Paid status is deliberately *not* a filter. Bills often go unmarked in the app
for weeks, so filtering on "unpaid" would list dozens of bills that are already
paid. Instead every bill due in the window is listed, and ones the app knows
are paid are tagged.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.models.enums import BillStatus
from app.schemas.schedule import PayPeriodOut

DEFAULT_WINDOW_DAYS = 3
MAX_WINDOW_DAYS = 31


@dataclass(frozen=True)
class DueSoonItem:
    name: str
    due_date: date
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

    @property
    def total(self) -> Decimal:
        return sum((item.amount for item in self.items), Decimal("0"))


def select_due_soon(
    periods: Sequence[PayPeriodOut],
    today: date,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> DueSoonDigest:
    """Bills due from ``today`` through ``today + window_days``, inclusive.

    On a payday (today is some period's effective pay date, including one
    moved earlier than its period start) the window stretches to the end of
    that pay period, so payday shows the whole period.

    Skipped bills are left out. Carried-over copies are kept: a bill moved to
    an earlier paycheck and never marked can survive only as a carried copy,
    and past-due carries are already outside the window. A bill that appears
    in more than one period is listed once.
    """
    if not 0 <= window_days <= MAX_WINDOW_DAYS:
        raise ValueError(
            f"window_days must be between 0 and {MAX_WINDOW_DAYS}, got {window_days}"
        )

    window_end = today + timedelta(days=window_days)
    payday_period = next((p for p in periods if p.pay_date == today), None)
    if payday_period is not None:
        window_end = max(window_end, payday_period.period_end)

    seen: set[tuple[int, date]] = set()
    items: list[DueSoonItem] = []
    for period in periods:
        for bill in period.assigned_bills:
            key = (bill.bill_id, bill.due_date)
            if (
                bill.status == BillStatus.skipped
                or not today <= bill.due_date <= window_end
                or key in seen
            ):
                continue
            seen.add(key)
            items.append(
                DueSoonItem(
                    name=bill.name,
                    due_date=bill.due_date,
                    amount=bill.actual_amount
                    if bill.actual_amount is not None
                    else bill.amount,
                    is_variable=bill.is_variable,
                    marked_paid=bill.status == BillStatus.paid,
                )
            )

    items.sort(key=lambda item: (item.due_date, item.name.lower()))
    return DueSoonDigest(
        today=today,
        window_end=window_end,
        window_days=window_days,
        is_payday=payday_period is not None,
        items=tuple(items),
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
            f"Payday: the whole pay period, {digest.today:%a %b %d} to "
            f"{digest.window_end:%a %b %d}."
        )
    else:
        lines.append(
            f"Next {digest.window_days} days: {digest.today:%a %b %d} to "
            f"{digest.window_end:%a %b %d}."
        )
    lines.append("")

    if not digest.items:
        lines.append("No bills due in this window.")
    else:
        for item in digest.items:
            approx = "~" if item.is_variable else ""
            paid = " (marked paid)" if item.marked_paid else ""
            amount = f"{approx}${item.amount:,.2f}"
            lines.append(f"- {item.due_date:%a %b %d}: {item.name}, {amount}{paid}")
        lines.append("")
        lines.append(f"Total: ${digest.total:,.2f} across {len(digest.items)} bills.")

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
