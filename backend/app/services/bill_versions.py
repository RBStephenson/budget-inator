from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Bill, BillVersion
from app.models.enums import BillRecurrence
from app.services.pay_period_engine import BillInput

VERSION_START = date(1, 1, 1)


def _bill_to_input(bill: Bill) -> BillInput:
    return BillInput(
        id=bill.id,
        name=bill.name,
        amount=Decimal(str(bill.estimated_amount)),
        recurrence=BillRecurrence(bill.recurrence),
        due_day=bill.due_day,
        first_due_date=bill.first_due_date,
        grace_period_days=bill.grace_period_days,
        due_day_is_month_end=bill.due_day_is_month_end,
        category=bill.category,
        is_variable=bill.is_variable,
        sinking_fund_enabled=bill.sinking_fund_enabled,
        is_active=bill.is_active,
    )


def _version_to_input(version: BillVersion) -> BillInput:
    return BillInput(
        id=version.bill_id,
        name=version.name,
        amount=Decimal(str(version.estimated_amount)),
        recurrence=BillRecurrence(version.recurrence),
        due_day=version.due_day,
        first_due_date=version.first_due_date,
        grace_period_days=version.grace_period_days,
        due_day_is_month_end=version.due_day_is_month_end,
        category=version.category,
        is_variable=version.is_variable,
        sinking_fund_enabled=version.sinking_fund_enabled,
        is_active=version.is_active,
    )


def _copy_bill_terms(
    bill: Bill, *, effective_date: date, existing: BillVersion | None = None
) -> BillVersion:
    target = existing or BillVersion(bill_id=bill.id, effective_date=effective_date)
    target.name = bill.name
    target.estimated_amount = bill.estimated_amount
    target.recurrence = bill.recurrence
    target.due_day = bill.due_day
    target.due_day_is_month_end = bill.due_day_is_month_end
    target.first_due_date = bill.first_due_date
    target.grace_period_days = bill.grace_period_days
    target.category = bill.category
    target.is_variable = bill.is_variable
    target.sinking_fund_enabled = bill.sinking_fund_enabled
    target.is_active = bill.is_active
    target.notes = bill.notes
    return target


def ensure_initial_version(db: Session, bill: Bill) -> None:
    """Create a baseline version for legacy/directly-created bills."""
    exists = (
        db.query(BillVersion)
        .filter(
            BillVersion.bill_id == bill.id, BillVersion.effective_date == VERSION_START
        )
        .first()
    )
    if exists is None:
        db.add(_copy_bill_terms(bill, effective_date=VERSION_START))


def record_bill_version(db: Session, bill: Bill, effective_date: date) -> BillVersion:
    existing = (
        db.query(BillVersion)
        .filter(
            BillVersion.bill_id == bill.id,
            BillVersion.effective_date == effective_date,
        )
        .first()
    )
    version = _copy_bill_terms(bill, effective_date=effective_date, existing=existing)
    if existing is None:
        db.add(version)
    return version


def bill_inputs_for_window(
    db: Session, bills: list[Bill], window_start: date, window_end: date
) -> list[BillInput]:
    if not bills:
        return []

    bill_ids = [b.id for b in bills]
    versions = (
        db.query(BillVersion)
        .filter(BillVersion.bill_id.in_(bill_ids))
        .order_by(BillVersion.bill_id, BillVersion.effective_date)
        .all()
    )
    by_bill: dict[int, list[BillVersion]] = {bill_id: [] for bill_id in bill_ids}
    for version in versions:
        by_bill[version.bill_id].append(version)

    inputs: list[BillInput] = []
    for bill in bills:
        bill_versions = by_bill.get(bill.id) or []
        if not bill_versions:
            bill_input = _bill_to_input(bill)
            if bill_input.is_active:
                inputs.append(bill_input)
            continue

        for index, version in enumerate(bill_versions):
            is_last = index + 1 >= len(bill_versions)
            active_start = max(window_start, version.effective_date)
            if is_last:
                # No successor version, so there's no known end date yet -
                # leave active_end unbounded rather than clamping it to this
                # window's end (which would hide the bill from any lookahead
                # past this window, e.g. sinking-fund due-date projection).
                active_end = None
            else:
                effective_end = bill_versions[index + 1].effective_date - timedelta(
                    days=1
                )
                active_end = min(window_end, effective_end)
                if active_start > active_end:
                    continue
            bill_input = _version_to_input(version)
            if bill_input.is_active:
                inputs.append(
                    replace(
                        bill_input,
                        active_start=active_start,
                        active_end=active_end,
                    )
                )
    return inputs


def bill_input_for_due_date(db: Session, bill: Bill, due_date: date) -> BillInput:
    version = (
        db.query(BillVersion)
        .filter(
            BillVersion.bill_id == bill.id,
            BillVersion.effective_date <= due_date,
        )
        .order_by(BillVersion.effective_date.desc())
        .first()
    )
    if version is not None:
        return _version_to_input(version)
    return _bill_to_input(bill)
