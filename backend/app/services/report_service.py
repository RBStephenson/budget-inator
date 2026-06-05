"""Assemble the data for the printable budget PDF report.

Reuses the existing schedule projection and monthly-summary builders so the
report always matches what the dashboard shows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Bill
from app.models.enums import BillRecurrence
from app.schemas.monthly import MonthlySummaryResponse
from app.schemas.schedule import ScheduleResponse
from app.services.schedule_service import build_monthly_summary, build_schedule

# Default number of pay periods in the report: current + next 5.
_DEFAULT_PERIOD_COUNT = 6

_ANNUAL_MULTIPLIER: dict[str, int] = {
    BillRecurrence.weekly: 52,
    BillRecurrence.biweekly: 26,
    BillRecurrence.monthly: 12,
    BillRecurrence.quarterly: 4,
    BillRecurrence.semiannual: 2,
    BillRecurrence.annual: 1,
    BillRecurrence.one_time: 1,
}

_RECURRENCE_LABEL: dict[str, str] = {
    BillRecurrence.monthly: "Monthly",
    BillRecurrence.biweekly: "Bi-weekly",
    BillRecurrence.weekly: "Weekly",
    BillRecurrence.quarterly: "Quarterly",
    BillRecurrence.semiannual: "Semi-annual",
    BillRecurrence.annual: "Annual",
    BillRecurrence.one_time: "One-time",
}


@dataclass
class ReportBillListItem:
    name: str
    category: str
    amount: Decimal
    annual_cost: Decimal
    recurrence_label: str
    due_label: str
    grace_days: int
    is_variable: bool


@dataclass
class ReportData:
    generated_on: date
    schedule: ScheduleResponse
    bill_list: list[ReportBillListItem]
    monthly: MonthlySummaryResponse


def _annual_cost(bill: Bill) -> Decimal:
    mult = _ANNUAL_MULTIPLIER.get(bill.recurrence, 1)
    return Decimal(str(bill.estimated_amount)) * mult


def _due_label(bill: Bill) -> str:
    if bill.recurrence == BillRecurrence.monthly:
        return f"Day {bill.due_day}"
    if bill.first_due_date is None:
        return "—"
    d = bill.first_due_date
    return f"{d:%b} {d.day}"


def _build_bill_list(db: Session) -> list[ReportBillListItem]:
    rows = db.query(Bill).filter(Bill.is_active.is_(True)).order_by(Bill.name).all()
    items: list[ReportBillListItem] = []
    for bill in rows:
        items.append(
            ReportBillListItem(
                name=bill.name,
                category=bill.category,
                amount=Decimal(str(bill.estimated_amount)),
                annual_cost=_annual_cost(bill),
                recurrence_label=_RECURRENCE_LABEL.get(
                    bill.recurrence, bill.recurrence
                ),
                due_label=_due_label(bill),
                grace_days=bill.grace_period_days,
                is_variable=bill.is_variable,
            )
        )
    return items


def build_report_data(
    db: Session,
    from_date: date | None = None,
    to_date: date | None = None,
) -> ReportData:
    """Gather the schedule, full bill list, and monthly summary for the PDF."""
    schedule = build_schedule(
        db, from_date, to_date, default_count=_DEFAULT_PERIOD_COUNT
    )

    # Derive the monthly-summary range from the schedule window.
    start = schedule.summary.from_date
    end = schedule.summary.to_date
    monthly = build_monthly_summary(
        db,
        from_month=f"{start.year:04d}-{start.month:02d}",
        to_month=f"{end.year:04d}-{end.month:02d}",
    )

    return ReportData(
        generated_on=date.today(),
        schedule=schedule,
        bill_list=_build_bill_list(db),
        monthly=monthly,
    )
