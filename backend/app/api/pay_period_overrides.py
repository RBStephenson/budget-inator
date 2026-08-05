from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pay_period_override import PayPeriodOverride
from app.services.upsert import upsert_or_update
from app.utils import utcnow

router = APIRouter(prefix="/pay-period-overrides", tags=["pay-period-overrides"])


class PayPeriodOverrideWrite(BaseModel):
    override_date: date


class PayPeriodOverrideOut(BaseModel):
    original_pay_date: date
    overridden_pay_date: date

    model_config = {"from_attributes": True}


@router.put("/{original_date}", response_model=PayPeriodOverrideOut)
def upsert_override(
    original_date: date,
    body: PayPeriodOverrideWrite,
    db: Session = Depends(get_db),
) -> PayPeriodOverride:
    if body.override_date == original_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="override_date must differ from original_date",
        )

    def lookup() -> PayPeriodOverride | None:
        return (
            db.query(PayPeriodOverride)
            .filter(PayPeriodOverride.original_pay_date == original_date)
            .first()
        )

    now = utcnow()

    def build() -> PayPeriodOverride:
        return PayPeriodOverride(
            original_pay_date=original_date,
            overridden_pay_date=body.override_date,
            created_at=now,
            updated_at=now,
        )

    def apply_update(existing: PayPeriodOverride) -> None:
        existing.overridden_pay_date = body.override_date
        existing.updated_at = now

    row = upsert_or_update(db, lookup, build, apply_update)

    db.commit()
    db.refresh(row)
    return row


@router.delete("/{original_date}", status_code=status.HTTP_204_NO_CONTENT)
def delete_override(
    original_date: date,
    db: Session = Depends(get_db),
) -> None:
    row = (
        db.query(PayPeriodOverride)
        .filter(PayPeriodOverride.original_pay_date == original_date)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No override found for this date",
        )
    db.delete(row)
    db.commit()
