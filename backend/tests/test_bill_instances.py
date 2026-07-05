"""Integration tests for PATCH /bill-instances/{bill_id}/{due_date}."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models import Bill, BillInstance


def _make_bill(db, name: str = "Rent") -> Bill:
    bill = Bill(
        name=name,
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


class TestUpsertBillInstance:
    def test_creates_paid_instance(self, client: TestClient, db):
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paid"
        assert data["bill_id"] == bill.id
        assert data["due_date"] == "2025-01-01"
        assert data["paid_at"] is not None

    def test_creates_skipped_instance(self, client: TestClient, db):
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "skipped"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "skipped"
        assert data["paid_at"] is None

    def test_creates_pending_instance(self, client: TestClient, db):
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "pending"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    def test_updates_existing_instance(self, client: TestClient, db):
        bill = _make_bill(db)
        client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid"},
        )
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "skipped"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "skipped"
        rows = db.query(BillInstance).filter(BillInstance.bill_id == bill.id).all()
        assert len(rows) == 1

    def test_stores_actual_amount(self, client: TestClient, db):
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid", "actual_amount": "750.00"},
        )
        assert resp.status_code == 200
        assert resp.json()["actual_amount"] == "750.00"

    def test_rejects_negative_actual_amount(self, client: TestClient, db):
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid", "actual_amount": "-1.00"},
        )
        assert resp.status_code == 422

    def test_marking_paid_preserves_actual_amount(self, client: TestClient, db):
        """Regression for #77: Paid without actual_amount must not wipe it."""
        bill = _make_bill(db)
        client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "pending", "actual_amount": "750.00"},
        )
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paid"
        assert data["actual_amount"] == "750.00"

    def test_undo_preserves_actual_amount(self, client: TestClient, db):
        bill = _make_bill(db)
        client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid", "actual_amount": "750.00"},
        )
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "pending"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["actual_amount"] == "750.00"

    def test_explicit_null_clears_actual_amount(self, client: TestClient, db):
        bill = _make_bill(db)
        client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "pending", "actual_amount": "750.00"},
        )
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "pending", "actual_amount": None},
        )
        assert resp.status_code == 200
        assert resp.json()["actual_amount"] is None

    def test_back_dates_paid_at_when_supplied(self, client: TestClient, db):
        """#69: an explicit paid_at is stored instead of the server time."""
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid", "paid_at": "2025-01-03T00:00:00"},
        )
        assert resp.status_code == 200
        assert resp.json()["paid_at"] == "2025-01-03T00:00:00"

    def test_accepts_date_only_paid_at(self, client: TestClient, db):
        """The frontend sends a YYYY-MM-DD date; it coerces to midnight."""
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid", "paid_at": "2025-01-03"},
        )
        assert resp.status_code == 200
        assert resp.json()["paid_at"].startswith("2025-01-03")

    def test_defaults_paid_at_to_now_when_omitted(self, client: TestClient, db):
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid"},
        )
        assert resp.status_code == 200
        assert resp.json()["paid_at"] is not None

    def test_back_dates_paid_at_on_existing_instance(self, client: TestClient, db):
        bill = _make_bill(db)
        client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "pending"},
        )
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "paid", "paid_at": "2024-12-28T00:00:00"},
        )
        assert resp.status_code == 200
        assert resp.json()["paid_at"] == "2024-12-28T00:00:00"

    def test_paid_at_ignored_for_non_paid_status(self, client: TestClient, db):
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "skipped", "paid_at": "2025-01-03T00:00:00"},
        )
        assert resp.status_code == 200
        assert resp.json()["paid_at"] is None

    def test_returns_404_for_unknown_bill(self, client: TestClient):
        resp = client.patch(
            "/bill-instances/9999/2025-01-01",
            json={"status": "paid"},
        )
        assert resp.status_code == 404

    def test_returns_422_for_invalid_status(self, client: TestClient, db):
        bill = _make_bill(db)
        resp = client.patch(
            f"/bill-instances/{bill.id}/2025-01-01",
            json={"status": "invalid"},
        )
        assert resp.status_code == 422
