from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bill, BillInstance
from app.models.enums import BillStatus
from app.utils import utcnow

router = APIRouter(prefix="/bill-instances", tags=["bill-instances"])


class BillInstanceWrite(BaseModel):
    status: BillStatus
    actual_amount: Decimal | None = None


class BillInstanceOut(BaseModel):
    id: int
    bill_id: int
    due_date: date
    estimated_amount: Decimal
    actual_amount: Decimal | None
    status: str
    paid_at: datetime | None

    model_config = {"from_attributes": True}


@router.patch("/{bill_id}/{due_date}", response_model=BillInstanceOut)
def upsert_bill_instance(
    bill_id: int,
    due_date: date,
    body: BillInstanceWrite,
    db: Session = Depends(get_db),
) -> BillInstance:
    bill = db.get(Bill, bill_id)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found"
        )

    inst = (
        db.query(BillInstance)
        .filter(BillInstance.bill_id == bill_id, BillInstance.due_date == due_date)
        .first()
    )

    now = utcnow()

    if inst is None:
        inst = BillInstance(
            bill_id=bill_id,
            pay_period_id=None,
            due_date=due_date,
            estimated_amount=bill.estimated_amount,
            actual_amount=body.actual_amount,
            status=body.status,
            paid_at=now if body.status == BillStatus.paid else None,
            created_at=now,
            updated_at=now,
        )
        db.add(inst)
    else:
        inst.status = body.status
        inst.actual_amount = body.actual_amount
        inst.paid_at = now if body.status == BillStatus.paid else None
        inst.updated_at = now

    db.commit()
    db.refresh(inst)
    return inst
