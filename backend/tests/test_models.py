from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Bill, BillInstance, PaySchedule
from app.models.enums import BillCategory, BillRecurrence, BillStatus, PayFrequency


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bill(db: Session, **kwargs) -> Bill:
    defaults = dict(
        name="Netflix",
        estimated_amount=Decimal("15.99"),
        recurrence=BillRecurrence.monthly,
        due_day=20,
        category=BillCategory.subscriptions,
        is_variable=False,
    )
    defaults.update(kwargs)
    bill = Bill(**defaults)
    db.add(bill)
    db.flush()
    return bill



# ---------------------------------------------------------------------------
# PayFrequency
# ---------------------------------------------------------------------------


class TestPayFrequency:
    def test_members(self):
        assert set(PayFrequency) == {
            PayFrequency.weekly,
            PayFrequency.biweekly,
            PayFrequency.semimonthly,
            PayFrequency.monthly,
        }

    def test_str_value(self):
        assert PayFrequency.biweekly == "biweekly"


# ---------------------------------------------------------------------------
# PaySchedule
# ---------------------------------------------------------------------------


class TestPaySchedule:
    def test_create(self, db):
        ps = PaySchedule(
            net_salary=Decimal("2500.00"),
            first_paycheck_date=date(2024, 1, 5),
            beginning_balance=Decimal("500.00"),
            frequency=PayFrequency.biweekly,
        )
        db.add(ps)
        db.commit()
        db.refresh(ps)

        assert ps.id == 1
        assert ps.net_salary == Decimal("2500.00")
        assert ps.beginning_balance == Decimal("500.00")
        assert ps.frequency == "biweekly"
        assert isinstance(ps.created_at, datetime)
        assert isinstance(ps.updated_at, datetime)

    def test_all_frequencies_accepted(self, db):
        for freq in PayFrequency:
            ps = PaySchedule(
                net_salary=Decimal("1000.00"),
                first_paycheck_date=date(2024, 1, 5),
                beginning_balance=Decimal("0.00"),
                frequency=freq,
            )
            db.add(ps)
        db.commit()


# ---------------------------------------------------------------------------
# BillCategory / BillRecurrence
# ---------------------------------------------------------------------------


class TestBillEnums:
    def test_category_members(self):
        assert set(BillCategory) == {
            BillCategory.housing,
            BillCategory.utilities,
            BillCategory.subscriptions,
            BillCategory.insurance,
            BillCategory.debt,
            BillCategory.savings,
            BillCategory.other,
        }

    def test_recurrence_members(self):
        assert set(BillRecurrence) == {
            BillRecurrence.weekly,
            BillRecurrence.biweekly,
            BillRecurrence.monthly,
            BillRecurrence.quarterly,
            BillRecurrence.semiannual,
            BillRecurrence.annual,
            BillRecurrence.one_time,
        }


# ---------------------------------------------------------------------------
# Bill
# ---------------------------------------------------------------------------


class TestBill:
    def test_create_monthly(self, db):
        bill = Bill(
            name="Rent",
            estimated_amount=Decimal("1200.00"),
            recurrence=BillRecurrence.monthly,
            due_day=1,
            grace_period_days=0,
            category=BillCategory.housing,
            is_variable=False,
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)

        assert bill.id == 1
        assert bill.name == "Rent"
        assert bill.is_active is True
        assert bill.is_variable is False
        assert bill.notes is None
        assert bill.first_due_date is None
        assert isinstance(bill.created_at, datetime)

    def test_create_variable_with_notes(self, db):
        bill = Bill(
            name="Electric",
            estimated_amount=Decimal("150.00"),
            recurrence=BillRecurrence.monthly,
            due_day=15,
            grace_period_days=3,
            category=BillCategory.utilities,
            is_variable=True,
            notes="Varies by season",
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)

        assert bill.is_variable is True
        assert bill.grace_period_days == 3
        assert bill.notes == "Varies by season"

    def test_create_biweekly_with_first_due_date(self, db):
        bill = Bill(
            name="Side payment",
            estimated_amount=Decimal("200.00"),
            recurrence=BillRecurrence.biweekly,
            first_due_date=date(2024, 1, 12),
            grace_period_days=0,
            category=BillCategory.debt,
            is_variable=False,
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)

        assert bill.due_day is None
        assert bill.first_due_date == date(2024, 1, 12)

    def test_default_grace_period(self, db):
        bill = _bill(db)
        db.commit()
        db.refresh(bill)
        assert bill.grace_period_days == 0

    def test_soft_delete_via_is_active(self, db):
        bill = _bill(db)
        db.commit()
        bill.is_active = False
        db.commit()
        db.refresh(bill)
        assert bill.is_active is False



# ---------------------------------------------------------------------------
# BillStatus
# ---------------------------------------------------------------------------


class TestBillStatus:
    def test_members(self):
        assert set(BillStatus) == {
            BillStatus.pending,
            BillStatus.paid,
            BillStatus.skipped,
        }

    def test_str_value(self):
        assert BillStatus.pending == "pending"


# ---------------------------------------------------------------------------
# BillInstance
# ---------------------------------------------------------------------------


class TestBillInstance:
    def test_create_pending(self, db):
        bill = _bill(db)
        instance = BillInstance(
            bill_id=bill.id,
            due_date=date(2024, 1, 20),
            estimated_amount=bill.estimated_amount,
        )
        db.add(instance)
        db.commit()
        db.refresh(instance)

        assert instance.id == 1
        assert instance.status == "pending"
        assert instance.actual_amount is None
        assert instance.paid_at is None

    def test_mark_paid(self, db):
        bill = _bill(db)
        paid_at = datetime(2024, 1, 15, 10, 30)
        instance = BillInstance(
            bill_id=bill.id,
            due_date=date(2024, 1, 20),
            estimated_amount=bill.estimated_amount,
            actual_amount=Decimal("14.99"),
            status=BillStatus.paid,
            paid_at=paid_at,
        )
        db.add(instance)
        db.commit()
        db.refresh(instance)

        assert instance.status == "paid"
        assert instance.actual_amount == Decimal("14.99")
        assert instance.paid_at == paid_at

    def test_mark_skipped(self, db):
        bill = _bill(db)
        instance = BillInstance(
            bill_id=bill.id,
            due_date=date(2024, 1, 20),
            estimated_amount=bill.estimated_amount,
            status=BillStatus.skipped,
        )
        db.add(instance)
        db.commit()
        db.refresh(instance)

        assert instance.status == "skipped"

    def test_relationship_bill(self, db):
        bill = _bill(db)
        db.add(
            BillInstance(
                bill_id=bill.id,
                due_date=date(2024, 1, 20),
                estimated_amount=bill.estimated_amount,
            )
        )
        db.commit()
        db.refresh(bill)

        assert len(bill.instances) == 1
        assert bill.instances[0].due_date == date(2024, 1, 20)

    def test_cascade_delete_bill_removes_instances(self, db):
        bill = _bill(db)
        db.add(
            BillInstance(
                bill_id=bill.id,
                due_date=date(2024, 1, 20),
                estimated_amount=bill.estimated_amount,
            )
        )
        db.commit()

        db.delete(bill)
        db.commit()

        assert db.query(BillInstance).count() == 0

    def test_unique_bill_due_date_constraint(self, db):
        bill = _bill(db)

        db.add(
            BillInstance(
                bill_id=bill.id,
                due_date=date(2024, 1, 20),
                estimated_amount=bill.estimated_amount,
            )
        )
        db.flush()

        db.add(
            BillInstance(
                bill_id=bill.id,
                due_date=date(2024, 1, 20),  # same bill + same due_date → violation
                estimated_amount=bill.estimated_amount,
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()

    def test_same_bill_different_due_dates_allowed(self, db):
        bill = _bill(db)

        db.add(
            BillInstance(
                bill_id=bill.id,
                due_date=date(2024, 1, 7),
                estimated_amount=bill.estimated_amount,
            )
        )
        db.add(
            BillInstance(
                bill_id=bill.id,
                due_date=date(2024, 1, 14),
                estimated_amount=bill.estimated_amount,
            )
        )
        db.commit()

        assert db.query(BillInstance).count() == 2
