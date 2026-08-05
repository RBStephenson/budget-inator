from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pay_period_actual import PayPeriodActual
from app.services.upsert import upsert_or_update
from app.utils import utcnow

router = APIRouter(prefix="/pay-period-actuals", tags=["pay-period-actuals"])


class PayPeriodActualWrite(BaseModel):
    actual_net_pay: Decimal | None = None
    actual_balance: Decimal | None = None

    @model_validator(mode="after")
    def at_least_one(self) -> PayPeriodActualWrite:
        if self.actual_net_pay is None and self.actual_balance is None:
            raise ValueError(
                "at least one of actual_net_pay or actual_balance is required"
            )
        return self

    @model_validator(mode="after")
    def non_negative(self) -> PayPeriodActualWrite:
        if self.actual_net_pay is not None and self.actual_net_pay < 0:
            raise ValueError("actual_net_pay must be >= 0")
        if self.actual_balance is not None and self.actual_balance < 0:
            raise ValueError("actual_balance must be >= 0")
        return self


class PayPeriodActualOut(BaseModel):
    pay_date: date
    actual_net_pay: Decimal | None
    actual_balance: Decimal | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[PayPeriodActualOut])
def list_actuals(db: Session = Depends(get_db)) -> list[PayPeriodActual]:
    return db.query(PayPeriodActual).order_by(PayPeriodActual.pay_date).all()


@router.put("/{pay_date}", response_model=PayPeriodActualOut)
def upsert_actual(
    pay_date: date,
    body: PayPeriodActualWrite,
    db: Session = Depends(get_db),
) -> PayPeriodActual:
    def lookup() -> PayPeriodActual | None:
        return (
            db.query(PayPeriodActual)
            .filter(PayPeriodActual.pay_date == pay_date)
            .first()
        )

    now = utcnow()

    def build() -> PayPeriodActual:
        return PayPeriodActual(
            pay_date=pay_date,
            actual_net_pay=body.actual_net_pay,
            actual_balance=body.actual_balance,
            created_at=now,
            updated_at=now,
        )

    def apply_update(existing: PayPeriodActual) -> None:
        existing.actual_net_pay = body.actual_net_pay
        existing.actual_balance = body.actual_balance
        existing.updated_at = now

    row = upsert_or_update(db, lookup, build, apply_update)

    db.commit()
    db.refresh(row)
    return row


@router.delete("/{pay_date}", status_code=status.HTTP_204_NO_CONTENT)
def delete_actual(pay_date: date, db: Session = Depends(get_db)) -> None:
    row = db.query(PayPeriodActual).filter(PayPeriodActual.pay_date == pay_date).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No actuals for that pay date"
        )
    db.delete(row)
    db.commit()
