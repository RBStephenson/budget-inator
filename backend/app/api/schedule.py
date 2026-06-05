from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.monthly import MonthlySummaryResponse
from app.schemas.schedule import ScheduleResponse
from app.services.schedule_service import build_monthly_summary, build_schedule

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("", response_model=ScheduleResponse)
def get_schedule(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    return build_schedule(db, from_date, to_date)


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
def get_monthly_summary(
    from_month: str | None = Query(default=None, alias="from"),
    to_month: str | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> MonthlySummaryResponse:
    return build_monthly_summary(db, from_month, to_month)
