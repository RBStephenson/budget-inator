from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.pdf_report import render_budget_pdf
from app.services.report_service import build_report_data

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/budget.pdf")
def get_budget_pdf(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> Response:
    report = build_report_data(db, from_date, to_date)
    pdf_bytes = render_budget_pdf(report)
    filename = f"budget-{report.schedule.summary.from_date.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
