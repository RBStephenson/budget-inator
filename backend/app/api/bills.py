from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bill
from app.models.enums import BillCategory, BillRecurrence
from app.schemas.bill import BillCreate, BillRead, BillUpdate

router = APIRouter(prefix="/bills", tags=["bills"])


def _validate_due_fields(bill: Bill, db: Session) -> None:
    """Reject a patched bill whose recurrence/due fields are inconsistent.

    Mirrors BillCreate.due_date_rules but checks the RESULTING state, so a
    partial PATCH (e.g. switching recurrence without supplying the matching
    due field) cannot persist a bill that breaks the schedule projection.
    """
    error: str | None = None
    if bill.recurrence == BillRecurrence.monthly:
        if bill.due_day_is_month_end and bill.due_day is not None:
            error = "due_day must be omitted when due_day_is_month_end is true"
        elif not bill.due_day_is_month_end and bill.due_day is None:
            error = "due_day is required unless due_day_is_month_end is true"
        elif bill.first_due_date is not None:
            error = "due_date must be omitted for monthly recurrence"
    else:
        if bill.first_due_date is None:
            error = "due_date is required for non-monthly recurrence"
        elif bill.due_day is not None:
            error = "due_day must be omitted for non-monthly recurrence"
        elif bill.due_day_is_month_end:
            error = "due_day_is_month_end must be false for non-monthly recurrence"

    if error is not None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error,
        )


def _get_bill_or_404(bill_id: int, db: Session) -> Bill:
    row = db.get(Bill, bill_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill {bill_id} not found",
        )
    return row


@router.get("", response_model=list[BillRead])
def list_bills(
    category: BillCategory | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Bill]:
    q = db.query(Bill).order_by(Bill.id)
    if category is not None:
        q = q.filter(Bill.category == category)
    return q.all()


@router.post("", response_model=BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(body: BillCreate, db: Session = Depends(get_db)) -> Bill:
    bill = Bill(
        name=body.name,
        estimated_amount=body.amount,
        recurrence=body.recurrence,
        due_day=body.due_day,
        due_day_is_month_end=body.due_day_is_month_end,
        first_due_date=body.due_date,
        grace_period_days=body.grace_period_days,
        category=body.category,
        is_variable=body.is_variable,
        notes=body.notes,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


@router.get("/{bill_id}", response_model=BillRead)
def get_bill(bill_id: int, db: Session = Depends(get_db)) -> Bill:
    return _get_bill_or_404(bill_id, db)


@router.patch("/{bill_id}", response_model=BillRead)
def patch_bill(bill_id: int, body: BillUpdate, db: Session = Depends(get_db)) -> Bill:
    bill = _get_bill_or_404(bill_id, db)

    if body.name is not None:
        bill.name = body.name
    if body.amount is not None:
        bill.estimated_amount = body.amount
    if body.recurrence is not None:
        bill.recurrence = body.recurrence
    if body.due_day is not None:
        bill.due_day = body.due_day
        bill.due_day_is_month_end = False
        # Clear the anchor date when switching to monthly
        if bill.recurrence == BillRecurrence.monthly:
            bill.first_due_date = None
    if body.due_day_is_month_end is not None:
        bill.due_day_is_month_end = body.due_day_is_month_end
        if body.due_day_is_month_end:
            bill.due_day = None
            if bill.recurrence == BillRecurrence.monthly:
                bill.first_due_date = None
    if body.due_date is not None:
        bill.first_due_date = body.due_date
        # Clear due_day when switching to a non-monthly anchor date
        if bill.recurrence != BillRecurrence.monthly:
            bill.due_day = None
            bill.due_day_is_month_end = False
    if body.grace_period_days is not None:
        bill.grace_period_days = body.grace_period_days
    if body.category is not None:
        bill.category = body.category
    if body.is_variable is not None:
        bill.is_variable = body.is_variable
    if body.is_active is not None:
        bill.is_active = body.is_active
    # Only update notes when the field was sent: omitting it preserves the
    # stored value, an explicit null clears it.
    if "notes" in body.model_fields_set:
        bill.notes = body.notes

    _validate_due_fields(bill, db)

    db.commit()
    db.refresh(bill)
    return bill


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(bill_id: int, db: Session = Depends(get_db)) -> None:
    bill = _get_bill_or_404(bill_id, db)
    bill.is_active = False
    db.commit()
