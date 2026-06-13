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


def _resolve_paid_at(body: BillInstanceWrite, now: datetime) -> datetime | None:
    """Timestamp to store for a payment.

    Only paid instances carry a ``paid_at``. When the caller supplied one we
    honor it (back-dating); otherwise we stamp the current server time.
    """
    if body.status != BillStatus.paid:
        return None
    if "paid_at" in body.model_fields_set and body.paid_at is not None:
        return body.paid_at
    return now


class BillInstanceWrite(BaseModel):
    status: BillStatus
    actual_amount: Decimal | None = None
    # When marking paid, lets the caller back-date the payment. Falls back to
    # the server time when omitted. Ignored unless status is paid.
    paid_at: datetime | None = None


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
    paid_at = _resolve_paid_at(body, now)

    if inst is None:
        inst = BillInstance(
            bill_id=bill_id,
            due_date=due_date,
            estimated_amount=bill.estimated_amount,
            actual_amount=body.actual_amount,
            status=body.status,
            paid_at=paid_at,
            created_at=now,
            updated_at=now,
        )
        db.add(inst)
    else:
        inst.status = body.status
        # Only update actual_amount when the field was sent: omitting it
        # preserves the stored value, an explicit null clears it.
        if "actual_amount" in body.model_fields_set:
            inst.actual_amount = body.actual_amount
        inst.paid_at = paid_at
        inst.updated_at = now

    db.commit()
    db.refresh(inst)
    return inst
