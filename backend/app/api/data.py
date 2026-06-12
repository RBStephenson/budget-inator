"""GET /data/export, POST /data/import, DELETE /data."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bill, BillInstance, PaySchedule
from app.models.enums import BillCategory, BillRecurrence, BillStatus, PayFrequency
from app.models.pay_period_actual import PayPeriodActual
from app.models.pay_period_override import PayPeriodOverride
from app.utils import utcnow

router = APIRouter(prefix="/data", tags=["data"])

EXPORT_VERSION = 3
# Older backups we can still restore. v2 simply has no pay_period_actuals.
SUPPORTED_IMPORT_VERSIONS = {2, 3}


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


class ExportBillInstance(BaseModel):
    # Index into the exported bills list (bill IDs are not stable across
    # import, so instances reference bills by position).
    bill_index: int
    due_date: date
    estimated_amount: Decimal
    actual_amount: Decimal | None
    status: BillStatus
    paid_at: datetime | None


class ExportPayPeriodOverride(BaseModel):
    original_pay_date: date
    overridden_pay_date: date


class ExportPayPeriodActual(BaseModel):
    pay_date: date
    actual_net_pay: Decimal | None
    actual_balance: Decimal | None


class ExportPayload(BaseModel):
    version: int
    pay_schedule: ExportPaySchedule | None
    bills: list[ExportBill]
    bill_instances: list[ExportBillInstance]
    pay_period_overrides: list[ExportPayPeriodOverride]
    pay_period_actuals: list[ExportPayPeriodActual]


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

    @field_validator("due_day")
    @classmethod
    def due_day_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 28):
            raise ValueError("due_day must be between 1 and 28")
        return v

    @model_validator(mode="after")
    def due_date_rules(self) -> ImportBill:
        if self.recurrence == BillRecurrence.monthly:
            if self.due_day is None:
                raise ValueError("due_day is required for monthly recurrence")
            if self.due_date is not None:
                raise ValueError("due_date must be omitted for monthly recurrence")
        else:
            if self.due_date is None:
                raise ValueError("due_date is required for non-monthly recurrence")
            if self.due_day is not None:
                raise ValueError("due_day must be omitted for non-monthly recurrence")
        return self


class ImportBillInstance(BaseModel):
    bill_index: int = Field(ge=0)
    due_date: date
    estimated_amount: Decimal
    actual_amount: Decimal | None = None
    status: BillStatus
    paid_at: datetime | None = None


class ImportPayPeriodOverride(BaseModel):
    original_pay_date: date
    overridden_pay_date: date

    @model_validator(mode="after")
    def dates_differ(self) -> ImportPayPeriodOverride:
        if self.original_pay_date == self.overridden_pay_date:
            raise ValueError("overridden_pay_date must differ from original_pay_date")
        return self


class ImportPayPeriodActual(BaseModel):
    pay_date: date
    actual_net_pay: Decimal | None = None
    actual_balance: Decimal | None = None

    @model_validator(mode="after")
    def at_least_one(self) -> ImportPayPeriodActual:
        if self.actual_net_pay is None and self.actual_balance is None:
            raise ValueError(
                "pay_period_actuals entries need actual_net_pay or actual_balance"
            )
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
    bill_instances: list[ImportBillInstance] = []
    pay_period_overrides: list[ImportPayPeriodOverride] = []
    pay_period_actuals: list[ImportPayPeriodActual] = []

    @field_validator("version")
    @classmethod
    def supported_version(cls, v: int) -> int:
        if v not in SUPPORTED_IMPORT_VERSIONS:
            raise ValueError(f"unsupported export version: {v}")
        return v

    @model_validator(mode="after")
    def referential_integrity(self) -> ImportPayload:
        seen_instances: set[tuple[int, date]] = set()
        for inst in self.bill_instances:
            if inst.bill_index >= len(self.bills):
                raise ValueError(
                    f"bill_instances references bill_index {inst.bill_index} "
                    f"but only {len(self.bills)} bills are present"
                )
            key = (inst.bill_index, inst.due_date)
            if key in seen_instances:
                raise ValueError(
                    f"duplicate bill instance for bill_index {inst.bill_index} "
                    f"on {inst.due_date}"
                )
            seen_instances.add(key)

        seen_overrides: set[date] = set()
        for ov in self.pay_period_overrides:
            if ov.original_pay_date in seen_overrides:
                raise ValueError(
                    f"duplicate pay-period override for {ov.original_pay_date}"
                )
            seen_overrides.add(ov.original_pay_date)

        seen_actuals: set[date] = set()
        for act in self.pay_period_actuals:
            if act.pay_date in seen_actuals:
                raise ValueError(f"duplicate pay-period actual for {act.pay_date}")
            seen_actuals.add(act.pay_date)
        return self


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/export", response_model=ExportPayload)
def export_data(db: Session = Depends(get_db)) -> ExportPayload:
    sched = db.query(PaySchedule).first()
    bills = db.query(Bill).order_by(Bill.id).all()
    instances = db.query(BillInstance).order_by(BillInstance.id).all()
    overrides = (
        db.query(PayPeriodOverride).order_by(PayPeriodOverride.original_pay_date).all()
    )
    actuals = db.query(PayPeriodActual).order_by(PayPeriodActual.pay_date).all()

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

    bill_index_by_id = {b.id: i for i, b in enumerate(bills)}
    export_instances = [
        ExportBillInstance(
            bill_index=bill_index_by_id[r.bill_id],
            due_date=r.due_date,
            estimated_amount=r.estimated_amount,
            actual_amount=r.actual_amount,
            status=BillStatus(r.status),
            paid_at=r.paid_at,
        )
        for r in instances
    ]

    export_overrides = [
        ExportPayPeriodOverride(
            original_pay_date=r.original_pay_date,
            overridden_pay_date=r.overridden_pay_date,
        )
        for r in overrides
    ]

    export_actuals = [
        ExportPayPeriodActual(
            pay_date=r.pay_date,
            actual_net_pay=r.actual_net_pay,
            actual_balance=r.actual_balance,
        )
        for r in actuals
    ]

    return ExportPayload(
        version=EXPORT_VERSION,
        pay_schedule=pay_schedule,
        bills=export_bills,
        bill_instances=export_instances,
        pay_period_overrides=export_overrides,
        pay_period_actuals=export_actuals,
    )


@router.post("/import", status_code=status.HTTP_204_NO_CONTENT)
def import_data(body: ImportPayload, db: Session = Depends(get_db)) -> None:
    # Delete all existing data in dependency order
    db.query(BillInstance).delete()
    db.query(PayPeriodOverride).delete()
    db.query(PayPeriodActual).delete()
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

    created_bills: list[Bill] = []
    for b in body.bills:
        bill = Bill(
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
        db.add(bill)
        created_bills.append(bill)

    # Flush so created bills get IDs for the instance FKs
    db.flush()

    for inst in body.bill_instances:
        db.add(
            BillInstance(
                bill_id=created_bills[inst.bill_index].id,
                pay_period_id=None,
                due_date=inst.due_date,
                estimated_amount=inst.estimated_amount,
                actual_amount=inst.actual_amount,
                status=inst.status,
                paid_at=inst.paid_at,
                created_at=now,
                updated_at=now,
            )
        )

    for ov in body.pay_period_overrides:
        db.add(
            PayPeriodOverride(
                original_pay_date=ov.original_pay_date,
                overridden_pay_date=ov.overridden_pay_date,
                created_at=now,
                updated_at=now,
            )
        )

    for act in body.pay_period_actuals:
        db.add(
            PayPeriodActual(
                pay_date=act.pay_date,
                actual_net_pay=act.actual_net_pay,
                actual_balance=act.actual_balance,
                created_at=now,
                updated_at=now,
            )
        )

    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_data(db: Session = Depends(get_db)) -> None:
    db.query(BillInstance).delete()
    db.query(PayPeriodOverride).delete()
    db.query(PayPeriodActual).delete()
    db.query(Bill).delete()
    db.query(PaySchedule).delete()
    db.commit()
