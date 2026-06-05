"""Tests for GET /data/export, POST /data/import, DELETE /data."""

from __future__ import annotations

from datetime import date

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


class TestExport:
    def test_export_empty_db(self, client: TestClient, db):
        resp = client.get("/data/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 1
        assert data["pay_schedule"] is None
        assert data["bills"] == []

    def test_export_with_data(self, client: TestClient, db):
        _seed(db)
        resp = client.get("/data/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 1
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


class TestImport:
    def test_import_replaces_all_data(self, client: TestClient, db):
        _seed(db)
        payload = {
            "version": 1,
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
        resp = client.post("/data/import", json={"version": 1, "bills": []})
        assert resp.status_code == 204
        export = client.get("/data/export").json()
        assert export["pay_schedule"] is None
        assert export["bills"] == []

    def test_import_rejects_wrong_version(self, client: TestClient, db):
        resp = client.post("/data/import", json={"version": 99, "bills": []})
        assert resp.status_code == 422

    def test_import_rejects_invalid_bill(self, client: TestClient, db):
        payload = {
            "version": 1,
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

    def test_import_clears_bill_instances_and_overrides(
        self, client: TestClient, db
    ):
        _seed(db)
        bill = db.query(Bill).first()
        db.add(
            BillInstance(
                bill_id=bill.id,
                due_date=date(2025, 1, 1),
                estimated_amount="1200.00",
                status="paid",
            )
        )
        db.add(
            PayPeriodOverride(
                original_pay_date=date(2025, 1, 3),
                overridden_pay_date=date(2025, 1, 2),
            )
        )
        db.commit()

        resp = client.post("/data/import", json={"version": 1, "bills": []})
        assert resp.status_code == 204
        assert db.query(BillInstance).count() == 0
        assert db.query(PayPeriodOverride).count() == 0


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

    def test_delete_clears_bill_instances_and_overrides(
        self, client: TestClient, db
    ):
        _seed(db)
        bill = db.query(Bill).first()
        db.add(
            BillInstance(
                bill_id=bill.id,
                due_date=date(2025, 1, 1),
                estimated_amount="1200.00",
                status="paid",
            )
        )
        db.add(
            PayPeriodOverride(
                original_pay_date=date(2025, 1, 3),
                overridden_pay_date=date(2025, 1, 2),
            )
        )
        db.commit()

        resp = client.delete("/data")
        assert resp.status_code == 204
        assert db.query(BillInstance).count() == 0
        assert db.query(PayPeriodOverride).count() == 0
