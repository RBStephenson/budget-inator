from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PaySchedule
from app.schemas.pay_schedule import PayScheduleCreate, PayScheduleRead, PayScheduleUpdate

router = APIRouter(prefix="/pay-schedule", tags=["pay-schedule"])


def _get_or_404(db: Session) -> PaySchedule:
    row = db.query(PaySchedule).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pay schedule configured")
    return row


@router.get("", response_model=PayScheduleRead)
def get_pay_schedule(db: Session = Depends(get_db)) -> PaySchedule:
    return _get_or_404(db)


@router.post("", response_model=PayScheduleRead, status_code=status.HTTP_201_CREATED)
def upsert_pay_schedule(body: PayScheduleCreate, db: Session = Depends(get_db)) -> PaySchedule:
    existing = db.query(PaySchedule).first()
    if existing is not None:
        db.delete(existing)
        db.flush()

    row = PaySchedule(
        net_salary=body.net_salary,
        first_paycheck_date=body.first_paycheck_date,
        beginning_balance=body.beginning_balance,
        frequency=body.frequency,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("", response_model=PayScheduleRead)
def patch_pay_schedule(body: PayScheduleUpdate, db: Session = Depends(get_db)) -> PaySchedule:
    row = _get_or_404(db)

    if body.net_salary is not None:
        row.net_salary = body.net_salary
    if body.first_paycheck_date is not None:
        row.first_paycheck_date = body.first_paycheck_date
    if body.beginning_balance is not None:
        row.beginning_balance = body.beginning_balance
    if body.frequency is not None:
        row.frequency = body.frequency

    db.commit()
    db.refresh(row)
    return row
