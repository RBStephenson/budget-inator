from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.monthly import MonthlySummaryResponse
from app.schemas.schedule import (
    RebalanceApplyRequest,
    RebalancePreviewRequest,
    RebalancePreviewResponse,
    ScheduleResponse,
    SmoothingPreviewRequest,
)
from app.services.schedule_service import (
    apply_rebalance_moves,
    build_monthly_summary,
    build_rebalance_preview,
    build_schedule,
    build_smoothing_preview,
)

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


@router.post("/rebalance-preview", response_model=RebalancePreviewResponse)
def preview_rebalance(
    body: RebalancePreviewRequest,
    db: Session = Depends(get_db),
) -> RebalancePreviewResponse:
    return build_rebalance_preview(db, body)


@router.post("/rebalance-apply", status_code=status.HTTP_204_NO_CONTENT)
def apply_rebalance(
    body: RebalanceApplyRequest,
    db: Session = Depends(get_db),
) -> None:
    apply_rebalance_moves(db, body)


@router.post("/smoothing-preview", response_model=RebalancePreviewResponse)
def preview_smoothing(
    body: SmoothingPreviewRequest,
    db: Session = Depends(get_db),
) -> RebalancePreviewResponse:
    return build_smoothing_preview(db, body.source_pay_date)
