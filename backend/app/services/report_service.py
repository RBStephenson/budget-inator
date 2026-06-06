"""Assemble the data for the printable budget PDF report.

Reuses the existing schedule projection and monthly-summary builders so the
report always matches what the dashboard shows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.schemas.monthly import MonthlySummaryResponse
from app.schemas.schedule import ScheduleResponse
from app.services.schedule_service import build_monthly_summary, build_schedule

# Default number of pay periods in the report: current + next 5.
_DEFAULT_PERIOD_COUNT = 6


@dataclass
class ReportData:
    generated_on: date
    schedule: ScheduleResponse
    monthly: MonthlySummaryResponse


def build_report_data(
    db: Session,
    from_date: date | None = None,
    to_date: date | None = None,
) -> ReportData:
    """Gather the schedule and monthly summary for the PDF."""
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
        monthly=monthly,
    )
