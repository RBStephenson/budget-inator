"""Tests for GET /data/export, POST /data/import, DELETE /data."""

from __future__ import annotations

from datetime import date, datetime

from fastapi.testclient import TestClient

from app.models import Bill, BillInstance, PaySchedule
from app.models.pay_period_override import PayPeriodOverride


def _seed(db) -> None:
    db.add(
        PaySchedule(
            net_salary="2000.00",
            first_paycheck_date=date(2025, 1, 3),
            beginning_balance="500.00",
            frequency="biweekly",
        )
    )
    db.add(
        Bill(
            name="Rent",
            estimated_amount="1200.00",
            recurrence="monthly",
            due_day=1,
            grace_period_days=0,
            category="housing",
            is_variable=False,
            is_active=True,
        )
    )
    db.commit()


def _seed_history(db) -> None:
    """Add a paid instance and a pay-date override on top of _seed."""
    bill = db.query(Bill).first()
    db.add(
        BillInstance(
            bill_id=bill.id,
            due_date=date(2025, 1, 1),
            estimated_amount="1200.00",
            actual_amount="1150.00",
            status="paid",
            paid_at=datetime(2025, 1, 1, 12, 0, 0),
        )
    )
    db.add(
        PayPeriodOverride(
            original_pay_date=date(2025, 1, 3),
            overridden_pay_date=date(2025, 1, 2),
        )
    )
    db.commit()


class TestExport:
    def test_export_empty_db(self, client: TestClient, db):
        resp = client.get("/data/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 2
        assert data["pay_schedule"] is None
        assert data["bills"] == []
        assert data["bill_instances"] == []
        assert data["pay_period_overrides"] == []

    def test_export_with_data(self, client: TestClient, db):
        _seed(db)
        resp = client.get("/data/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 2
        assert data["pay_schedule"]["net_salary"] == "2000.00"
        assert data["pay_schedule"]["frequency"] == "biweekly"
        assert len(data["bills"]) == 1
        assert data["bills"][0]["name"] == "Rent"
        assert data["bills"][0]["amount"] == "1200.00"
        assert data["bills"][0]["recurrence"] == "monthly"

    def test_export_includes_inactive_bills(self, client: TestClient, db):
        db.add(
            Bill(
                name="Old Bill",
                estimated_amount="50.00",
                recurrence="monthly",
                due_day=15,
                grace_period_days=0,
                category="other",
                is_variable=False,
                is_active=False,
            )
        )
        db.commit()
        resp = client.get("/data/export")
        bills = resp.json()["bills"]
        assert any(b["name"] == "Old Bill" for b in bills)
        assert any(not b["is_active"] for b in bills)

    def test_export_includes_instances_and_overrides(self, client: TestClient, db):
        _seed(db)
        _seed_history(db)
        resp = client.get("/data/export")
        data = resp.json()

        assert len(data["bill_instances"]) == 1
        inst = data["bill_instances"][0]
        assert inst["bill_index"] == 0
        assert inst["due_date"] == "2025-01-01"
        assert inst["estimated_amount"] == "1200.00"
        assert inst["actual_amount"] == "1150.00"
        assert inst["status"] == "paid"
        assert inst["paid_at"] is not None

        assert len(data["pay_period_overrides"]) == 1
        ov = data["pay_period_overrides"][0]
        assert ov["original_pay_date"] == "2025-01-03"
        assert ov["overridden_pay_date"] == "2025-01-02"

    def test_export_bill_index_matches_bill_position(self, client: TestClient, db):
        _seed(db)
        second = Bill(
            name="Electric",
            estimated_amount="150.00",
            recurrence="monthly",
            due_day=15,
            grace_period_days=0,
            category="utilities",
            is_variable=True,
            is_active=True,
        )
        db.add(second)
        db.commit()
        db.add(
            BillInstance(
                bill_id=second.id,
                due_date=date(2025, 1, 15),
                estimated_amount="150.00",
                status="skipped",
            )
        )
        db.commit()

        data = client.get("/data/export").json()
        inst = data["bill_instances"][0]
        assert data["bills"][inst["bill_index"]]["name"] == "Electric"


class TestImport:
    def test_import_replaces_all_data(self, client: TestClient, db):
        _seed(db)
        payload = {
            "version": 2,
            "pay_schedule": {
                "net_salary": "3000.00",
                "first_paycheck_date": "2025-02-01",
                "beginning_balance": "100.00",
                "frequency": "monthly",
            },
            "bills": [
                {
                    "name": "Internet",
                    "amount": "60.00",
                    "recurrence": "monthly",
                    "due_day": 5,
                    "due_date": None,
                    "grace_period_days": 3,
                    "category": "utilities",
                    "is_variable": False,
                    "is_active": True,
                    "notes": None,
                }
            ],
        }
        resp = client.post("/data/import", json=payload)
        assert resp.status_code == 204

        export = client.get("/data/export").json()
        assert export["pay_schedule"]["net_salary"] == "3000.00"
        assert len(export["bills"]) == 1
        assert export["bills"][0]["name"] == "Internet"

    def test_import_empty_payload_wipes_data(self, client: TestClient, db):
        _seed(db)
        resp = client.post("/data/import", json={"version": 2, "bills": []})
        assert resp.status_code == 204
        export = client.get("/data/export").json()
        assert export["pay_schedule"] is None
        assert export["bills"] == []

    def test_import_rejects_wrong_version(self, client: TestClient, db):
        resp = client.post("/data/import", json={"version": 99, "bills": []})
        assert resp.status_code == 422

    def test_import_rejects_v1_payload(self, client: TestClient, db):
        resp = client.post("/data/import", json={"version": 1, "bills": []})
        assert resp.status_code == 422

    def test_import_rejects_invalid_bill(self, client: TestClient, db):
        payload = {
            "version": 2,
            "bills": [
                {
                    "name": "Bad",
                    "amount": "-10.00",
                    "recurrence": "monthly",
                    "due_day": 1,
                    "due_date": None,
                    "grace_period_days": 0,
                    "category": "other",
                    "is_variable": False,
                    "is_active": True,
                    "notes": None,
                }
            ],
        }
        resp = client.post("/data/import", json=payload)
        assert resp.status_code == 422

    def test_import_rejects_out_of_range_bill_index(self, client: TestClient, db):
        payload = {
            "version": 2,
            "bills": [],
            "bill_instances": [
                {
                    "bill_index": 0,
                    "due_date": "2025-01-01",
                    "estimated_amount": "100.00",
                    "status": "paid",
                }
            ],
        }
        resp = client.post("/data/import", json=payload)
        assert resp.status_code == 422

    def test_import_rejects_duplicate_instances(self, client: TestClient, db):
        instance = {
            "bill_index": 0,
            "due_date": "2025-01-01",
            "estimated_amount": "100.00",
            "status": "paid",
        }
        payload = {
            "version": 2,
            "bills": [
                {
                    "name": "Rent",
                    "amount": "100.00",
                    "recurrence": "monthly",
                    "due_day": 1,
                    "category": "housing",
                }
            ],
            "bill_instances": [instance, dict(instance)],
        }
        resp = client.post("/data/import", json=payload)
        assert resp.status_code == 422

    def test_import_rejects_duplicate_overrides(self, client: TestClient, db):
        payload = {
            "version": 2,
            "bills": [],
            "pay_period_overrides": [
                {
                    "original_pay_date": "2025-01-03",
                    "overridden_pay_date": "2025-01-02",
                },
                {
                    "original_pay_date": "2025-01-03",
                    "overridden_pay_date": "2025-01-04",
                },
            ],
        }
        resp = client.post("/data/import", json=payload)
        assert resp.status_code == 422

    def test_import_without_history_clears_instances_and_overrides(
        self, client: TestClient, db
    ):
        _seed(db)
        _seed_history(db)

        resp = client.post("/data/import", json={"version": 2, "bills": []})
        assert resp.status_code == 204
        assert db.query(BillInstance).count() == 0
        assert db.query(PayPeriodOverride).count() == 0

    def test_export_import_round_trip_preserves_history(self, client: TestClient, db):
        """Regression for #78: backup → restore must keep payment history."""
        _seed(db)
        _seed_history(db)

        backup = client.get("/data/export").json()
        resp = client.post("/data/import", json=backup)
        assert resp.status_code == 204

        restored = client.get("/data/export").json()
        assert restored["pay_schedule"] == backup["pay_schedule"]
        assert restored["bills"] == backup["bills"]
        assert restored["bill_instances"] == backup["bill_instances"]
        assert restored["pay_period_overrides"] == backup["pay_period_overrides"]

        # And the rows really exist with the right values
        inst = db.query(BillInstance).one()
        assert str(inst.actual_amount) == "1150.00"
        assert inst.status == "paid"
        assert inst.paid_at == datetime(2025, 1, 1, 12, 0, 0)
        ov = db.query(PayPeriodOverride).one()
        assert ov.overridden_pay_date == date(2025, 1, 2)


class TestDelete:
    def test_delete_wipes_all_data(self, client: TestClient, db):
        _seed(db)
        resp = client.delete("/data")
        assert resp.status_code == 204
        assert db.query(PaySchedule).count() == 0
        assert db.query(Bill).count() == 0

    def test_delete_is_idempotent(self, client: TestClient, db):
        resp = client.delete("/data")
        assert resp.status_code == 204

    def test_delete_clears_bill_instances_and_overrides(self, client: TestClient, db):
        _seed(db)
        _seed_history(db)

        resp = client.delete("/data")
        assert resp.status_code == 204
        assert db.query(BillInstance).count() == 0
        assert db.query(PayPeriodOverride).count() == 0
