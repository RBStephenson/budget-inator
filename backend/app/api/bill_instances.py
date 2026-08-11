from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bill, BillInstance
from app.models.enums import BillStatus
from app.services.bill_versions import bill_input_for_due_date
from app.services.upsert import upsert_or_update
from app.utils import utcnow

router = APIRouter(prefix="/bill-instances", tags=["bill-instances"])


def _today_local() -> date:
    """The calendar date `paid_at` defaults to when the caller omits one.

    Deliberately the server's local system date, not `utcnow()`'s UTC date:
    this is a single-user local app where the backend and the user share a
    machine, so the server's local clock already matches the user's. Using
    UTC here let a payment's `.date()` land on the wrong calendar day (and
    therefore the wrong pay period) whenever the user's local evening had
    already rolled past midnight UTC (BI-15).
    """
    return date.today()


def _resolve_paid_at(body: BillInstanceWrite) -> datetime | None:
    """Timestamp to store for a payment.

    Only paid instances carry a ``paid_at``. When the caller supplied one we
    honor it (back-dating); otherwise we stamp today's local calendar date.
    """
    if body.status != BillStatus.paid:
        return None
    if "paid_at" in body.model_fields_set and body.paid_at is not None:
        return body.paid_at
    return datetime.combine(_today_local(), datetime.min.time())


class BillInstanceWrite(BaseModel):
    status: BillStatus
    actual_amount: Decimal | None = Field(default=None, ge=0)
    # When marking paid, lets the caller back-date the payment. Falls back to
    # the server time when omitted. Ignored unless status is paid.
    paid_at: datetime | None = None
    # Optional manual placement for unpaid bills. The schedule uses the period
    # containing this payday instead of the inferred due-date period.
    manual_pay_date: date | None = None


class BillInstanceOut(BaseModel):
    id: int
    bill_id: int
    due_date: date
    estimated_amount: Decimal
    actual_amount: Decimal | None
    status: str
    paid_at: datetime | None
    manual_pay_date: date | None

    model_config = {"from_attributes": True}


@router.get("/{bill_id}", response_model=list[BillInstanceOut])
def list_bill_instances(
    bill_id: int,
    db: Session = Depends(get_db),
) -> list[BillInstance]:
    bill = db.get(Bill, bill_id)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found"
        )
    return (
        db.query(BillInstance)
        .filter(BillInstance.bill_id == bill_id)
        .order_by(BillInstance.due_date.desc())
        .all()
    )


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

    def lookup() -> BillInstance | None:
        return (
            db.query(BillInstance)
            .filter(BillInstance.bill_id == bill_id, BillInstance.due_date == due_date)
            .first()
        )

    now = utcnow()
    paid_at = _resolve_paid_at(body)
    bill_terms = bill_input_for_due_date(db, bill, due_date)

    def build() -> BillInstance:
        return BillInstance(
            bill_id=bill_id,
            due_date=due_date,
            estimated_amount=bill_terms.amount,
            actual_amount=body.actual_amount,
            status=body.status,
            paid_at=paid_at,
            manual_pay_date=body.manual_pay_date,
            created_at=now,
            updated_at=now,
        )

    def apply_update(existing: BillInstance) -> None:
        existing.status = body.status
        # Only update actual_amount when the field was sent: omitting it
        # preserves the stored value, an explicit null clears it.
        if "actual_amount" in body.model_fields_set:
            existing.actual_amount = body.actual_amount
        if "manual_pay_date" in body.model_fields_set:
            existing.manual_pay_date = body.manual_pay_date
        existing.paid_at = paid_at
        existing.updated_at = now

    inst = upsert_or_update(db, lookup, build, apply_update)

    db.commit()
    db.refresh(inst)
    return inst
