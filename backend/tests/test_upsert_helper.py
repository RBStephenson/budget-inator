"""Tests for the shared upsert-or-update retry helper (BI-19).

A plain query-then-insert is racy: two requests for the same unique key can
both see no row on their initial lookup and both attempt an insert. The
loser's insert violates the unique constraint. These tests reproduce that
outcome directly against a real SQLite `IntegrityError` (rather than actual
thread concurrency, which the shared single-connection test fixture can't
express) by handing the helper a `lookup` that lies and returns `None` even
though a conflicting row already exists, forcing it down the retry path.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Bill, BillInstance
from app.models.enums import BillStatus
from app.models.pay_period_override import PayPeriodOverride
from app.services.upsert import upsert_or_update
from app.utils import utcnow


def _make_bill(db) -> Bill:
    bill = Bill(
        name="Rent",
        estimated_amount="800.00",
        recurrence="monthly",
        due_day=1,
        first_due_date=None,
        grace_period_days=0,
        category="housing",
        is_variable=False,
        is_active=True,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


class TestUpsertOrUpdate:
    def test_found_on_lookup_updates_without_building(self, db):
        db.add(
            PayPeriodOverride(
                original_pay_date=date(2025, 1, 3),
                overridden_pay_date=date(2025, 1, 2),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        db.commit()

        def lookup() -> PayPeriodOverride | None:
            return (
                db.query(PayPeriodOverride)
                .filter(PayPeriodOverride.original_pay_date == date(2025, 1, 3))
                .first()
            )

        def build() -> PayPeriodOverride:
            raise AssertionError("build() must not run when lookup() finds a row")

        def apply_update(existing: PayPeriodOverride) -> None:
            existing.overridden_pay_date = date(2025, 1, 1)

        row = upsert_or_update(db, lookup, build, apply_update)
        db.commit()

        assert row.overridden_pay_date == date(2025, 1, 1)
        assert db.query(PayPeriodOverride).count() == 1

    def test_not_found_creates_row(self, db):
        def lookup() -> PayPeriodOverride | None:
            return (
                db.query(PayPeriodOverride)
                .filter(PayPeriodOverride.original_pay_date == date(2025, 1, 3))
                .first()
            )

        def build() -> PayPeriodOverride:
            return PayPeriodOverride(
                original_pay_date=date(2025, 1, 3),
                overridden_pay_date=date(2025, 1, 2),
                created_at=utcnow(),
                updated_at=utcnow(),
            )

        def apply_update(existing: PayPeriodOverride) -> None:
            raise AssertionError("apply_update() must not run on a fresh insert")

        row = upsert_or_update(db, lookup, build, apply_update)
        db.commit()

        assert row.overridden_pay_date == date(2025, 1, 2)
        assert db.query(PayPeriodOverride).count() == 1

    def test_lost_race_falls_back_to_update_instead_of_raising(self, db):
        """The `PayPeriodOverride` case: a single-field unique key."""
        winner = PayPeriodOverride(
            original_pay_date=date(2025, 1, 3),
            overridden_pay_date=date(2025, 1, 2),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(winner)
        db.commit()

        def lying_lookup() -> PayPeriodOverride | None:
            return None

        def real_lookup() -> PayPeriodOverride | None:
            return (
                db.query(PayPeriodOverride)
                .filter(PayPeriodOverride.original_pay_date == date(2025, 1, 3))
                .first()
            )

        calls = {"n": 0}

        def one_shot_lying_lookup() -> PayPeriodOverride | None:
            calls["n"] += 1
            return lying_lookup() if calls["n"] == 1 else real_lookup()

        def build() -> PayPeriodOverride:
            return PayPeriodOverride(
                original_pay_date=date(2025, 1, 3),
                overridden_pay_date=date(2025, 1, 5),
                created_at=utcnow(),
                updated_at=utcnow(),
            )

        def apply_update(existing: PayPeriodOverride) -> None:
            existing.overridden_pay_date = date(2025, 1, 9)

        row = upsert_or_update(db, one_shot_lying_lookup, build, apply_update)
        db.commit()

        assert row.id == winner.id
        assert row.overridden_pay_date == date(2025, 1, 9)
        assert db.query(PayPeriodOverride).count() == 1

    def test_lost_race_on_multi_field_model(self, db):
        """The `BillInstance` case: composite unique key, partial-update shape."""
        bill = _make_bill(db)
        winner = BillInstance(
            bill_id=bill.id,
            due_date=date(2025, 1, 1),
            estimated_amount="800.00",
            status=BillStatus.pending,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(winner)
        db.commit()

        calls = {"n": 0}

        def lookup() -> BillInstance | None:
            calls["n"] += 1
            if calls["n"] == 1:
                return None
            return (
                db.query(BillInstance)
                .filter(
                    BillInstance.bill_id == bill.id,
                    BillInstance.due_date == date(2025, 1, 1),
                )
                .first()
            )

        def build() -> BillInstance:
            return BillInstance(
                bill_id=bill.id,
                due_date=date(2025, 1, 1),
                estimated_amount="800.00",
                status=BillStatus.paid,
                created_at=utcnow(),
                updated_at=utcnow(),
            )

        def apply_update(existing: BillInstance) -> None:
            existing.status = BillStatus.paid

        row = upsert_or_update(db, lookup, build, apply_update)
        db.commit()

        assert row.id == winner.id
        assert row.status == BillStatus.paid
        assert db.query(BillInstance).count() == 1

    def test_session_stays_usable_after_a_lost_race(self, db):
        """A losing insert's retry rolls back the *whole* transaction (SQLite
        SAVEPOINTs aren't usable here without extra connection-level event
        wiring this app doesn't have). `apply_rebalance_moves` accounts for
        this by committing after each move instead of batching one commit
        for the whole request (see its own code comment) rather than relying
        on this helper to scope the rollback narrowly. This test just proves
        the session recovers cleanly and isn't left broken after a retry.
        """
        bill = _make_bill(db)
        winner = BillInstance(
            bill_id=bill.id,
            due_date=date(2025, 1, 1),
            estimated_amount="800.00",
            status=BillStatus.pending,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(winner)
        db.commit()

        calls = {"n": 0}

        def lookup() -> BillInstance | None:
            calls["n"] += 1
            if calls["n"] == 1:
                return None
            return (
                db.query(BillInstance)
                .filter(
                    BillInstance.bill_id == bill.id,
                    BillInstance.due_date == date(2025, 1, 1),
                )
                .first()
            )

        def build() -> BillInstance:
            return BillInstance(
                bill_id=bill.id,
                due_date=date(2025, 1, 1),
                estimated_amount="800.00",
                status=BillStatus.paid,
                created_at=utcnow(),
                updated_at=utcnow(),
            )

        def apply_update(existing: BillInstance) -> None:
            existing.status = BillStatus.paid

        upsert_or_update(db, lookup, build, apply_update)
        db.commit()

        # Session must still be usable for further, unrelated writes.
        later_move = BillInstance(
            bill_id=bill.id,
            due_date=date(2025, 2, 1),
            estimated_amount="800.00",
            status=BillStatus.pending,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(later_move)
        db.commit()

        assert (
            db.query(BillInstance)
            .filter(
                BillInstance.bill_id == bill.id,
                BillInstance.due_date == date(2025, 2, 1),
            )
            .first()
            is not None
        )

    def test_reraises_when_conflict_row_is_unexplainably_missing(self, db):
        def lookup() -> PayPeriodOverride | None:
            return None

        def build() -> PayPeriodOverride:
            # Two builds with the same key inside one flush both fail to
            # resolve to a real row on re-lookup because neither is ever
            # committed under a different key here — simplest way to force
            # the "conflict but re-lookup still finds nothing" branch is to
            # violate a different NOT NULL/type constraint, but the cleanest
            # deterministic trigger is a duplicate primary key with a lookup
            # that filters on a column no built row will ever match.
            return PayPeriodOverride(
                original_pay_date=date(2025, 1, 3),
                overridden_pay_date=date(2025, 1, 2),
                created_at=utcnow(),
                updated_at=utcnow(),
            )

        def apply_update(existing: PayPeriodOverride) -> None:
            pass

        # Pre-seed a real conflicting row so the flush raises, but keep the
        # lookup always returning None (not one-shot) so the retry can't
        # find it either -- proving the helper re-raises rather than
        # swallowing a conflict it can't resolve.
        db.add(
            PayPeriodOverride(
                original_pay_date=date(2025, 1, 3),
                overridden_pay_date=date(2025, 1, 2),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        db.commit()

        with pytest.raises(IntegrityError):
            upsert_or_update(db, lookup, build, apply_update)
