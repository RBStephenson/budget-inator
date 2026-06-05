"""GET /data/export, POST /data/import, DELETE /data."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bill, BillInstance, PaySchedule
from app.models.enums import BillCategory, BillRecurrence, PayFrequency
from app.models.pay_period_override import PayPeriodOverride
from app.utils import utcnow

router = APIRouter(prefix="/data", tags=["data"])

EXPORT_VERSION = 1


# ── Schemas ──────────────────────────────────────────────────────────────────


class ExportPaySchedule(BaseModel):
    net_salary: Decimal
    first_paycheck_date: date
    beginning_balance: Decimal
    frequency: PayFrequency


class ExportBill(BaseModel):
    name: str
    amount: Decimal
    recurrence: BillRecurrence
    due_day: int | None
    due_date: date | None
    grace_period_days: int
    category: BillCategory
    is_variable: bool
    is_active: bool
    notes: str | None


class ExportPayload(BaseModel):
    version: int
    pay_schedule: ExportPaySchedule | None
    bills: list[ExportBill]


class ImportBill(BaseModel):
    name: str
    amount: Decimal
    recurrence: BillRecurrence
    due_day: int | None = None
    due_date: date | None = None
    grace_period_days: int = Field(default=0, ge=0)
    category: BillCategory
    is_variable: bool = False
    is_active: bool = True
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @model_validator(mode="after")
    def due_date_rules(self) -> ImportBill:
        if self.recurrence == BillRecurrence.monthly:
            if self.due_day is None:
                raise ValueError("due_day is required for monthly recurrence")
        else:
            if self.due_date is None:
                raise ValueError("due_date is required for non-monthly recurrence")
        return self


class ImportPaySchedule(BaseModel):
    net_salary: Decimal
    first_paycheck_date: date
    beginning_balance: Decimal
    frequency: PayFrequency

    @field_validator("net_salary", "beginning_balance")
    @classmethod
    def non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("must be >= 0")
        return v


class ImportPayload(BaseModel):
    version: int
    pay_schedule: ImportPaySchedule | None = None
    bills: list[ImportBill] = []

    @field_validator("version")
    @classmethod
    def supported_version(cls, v: int) -> int:
        if v != EXPORT_VERSION:
            raise ValueError(f"unsupported export version: {v}")
        return v


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/export", response_model=ExportPayload)
def export_data(db: Session = Depends(get_db)) -> ExportPayload:
    sched = db.query(PaySchedule).first()
    bills = db.query(Bill).order_by(Bill.id).all()

    pay_schedule = None
    if sched is not None:
        pay_schedule = ExportPaySchedule(
            net_salary=sched.net_salary,
            first_paycheck_date=sched.first_paycheck_date,
            beginning_balance=sched.beginning_balance,
            frequency=PayFrequency(sched.frequency),
        )

    export_bills = [
        ExportBill(
            name=b.name,
            amount=b.estimated_amount,
            recurrence=BillRecurrence(b.recurrence),
            due_day=b.due_day,
            due_date=b.first_due_date,
            grace_period_days=b.grace_period_days,
            category=BillCategory(b.category),
            is_variable=b.is_variable,
            is_active=b.is_active,
            notes=b.notes,
        )
        for b in bills
    ]

    return ExportPayload(
        version=EXPORT_VERSION,
        pay_schedule=pay_schedule,
        bills=export_bills,
    )


@router.post("/import", status_code=status.HTTP_204_NO_CONTENT)
def import_data(body: ImportPayload, db: Session = Depends(get_db)) -> None:
    # Delete all existing data in dependency order
    db.query(BillInstance).delete()
    db.query(PayPeriodOverride).delete()
    db.query(Bill).delete()
    db.query(PaySchedule).delete()

    now = utcnow()

    if body.pay_schedule is not None:
        ps = body.pay_schedule
        db.add(
            PaySchedule(
                net_salary=ps.net_salary,
                first_paycheck_date=ps.first_paycheck_date,
                beginning_balance=ps.beginning_balance,
                frequency=ps.frequency,
                created_at=now,
                updated_at=now,
            )
        )

    for b in body.bills:
        db.add(
            Bill(
                name=b.name,
                estimated_amount=b.amount,
                recurrence=b.recurrence,
                due_day=b.due_day,
                first_due_date=b.due_date,
                grace_period_days=b.grace_period_days,
                category=b.category,
                is_variable=b.is_variable,
                is_active=b.is_active,
                notes=b.notes,
                created_at=now,
                updated_at=now,
            )
        )

    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_data(db: Session = Depends(get_db)) -> None:
    db.query(BillInstance).delete()
    db.query(PayPeriodOverride).delete()
    db.query(Bill).delete()
    db.query(PaySchedule).delete()
    db.commit()
