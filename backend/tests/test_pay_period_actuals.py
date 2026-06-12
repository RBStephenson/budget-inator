"""Integration tests for /pay-period-actuals (#55)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models import PayPeriodActual


class TestUpsertActual:
    def test_creates_with_both_fields(self, client: TestClient, db):
        resp = client.put(
            "/pay-period-actuals/2025-01-03",
            json={"actual_net_pay": "2100.00", "actual_balance": "3450.00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pay_date"] == "2025-01-03"
        assert data["actual_net_pay"] == "2100.00"
        assert data["actual_balance"] == "3450.00"

    def test_creates_with_balance_only(self, client: TestClient, db):
        resp = client.put(
            "/pay-period-actuals/2025-01-03",
            json={"actual_balance": "3450.00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["actual_net_pay"] is None
        assert data["actual_balance"] == "3450.00"

    def test_updates_existing(self, client: TestClient, db):
        client.put("/pay-period-actuals/2025-01-03", json={"actual_balance": "3000.00"})
        resp = client.put(
            "/pay-period-actuals/2025-01-03",
            json={"actual_net_pay": "2100.00", "actual_balance": "3450.00"},
        )
        assert resp.status_code == 200
        assert resp.json()["actual_net_pay"] == "2100.00"
        rows = db.query(PayPeriodActual).all()
        assert len(rows) == 1

    def test_rejects_empty_body(self, client: TestClient, db):
        resp = client.put("/pay-period-actuals/2025-01-03", json={})
        assert resp.status_code == 422

    def test_rejects_negative(self, client: TestClient, db):
        resp = client.put(
            "/pay-period-actuals/2025-01-03", json={"actual_balance": "-5.00"}
        )
        assert resp.status_code == 422


class TestListActuals:
    def test_lists_in_date_order(self, client: TestClient, db):
        client.put("/pay-period-actuals/2025-02-14", json={"actual_balance": "10.00"})
        client.put("/pay-period-actuals/2025-01-03", json={"actual_balance": "20.00"})
        resp = client.get("/pay-period-actuals")
        assert resp.status_code == 200
        dates = [r["pay_date"] for r in resp.json()]
        assert dates == ["2025-01-03", "2025-02-14"]


class TestDeleteActual:
    def test_deletes(self, client: TestClient, db):
        client.put("/pay-period-actuals/2025-01-03", json={"actual_balance": "20.00"})
        resp = client.delete("/pay-period-actuals/2025-01-03")
        assert resp.status_code == 204
        assert db.query(PayPeriodActual).count() == 0

    def test_delete_unknown_returns_404(self, client: TestClient, db):
        resp = client.delete("/pay-period-actuals/2025-01-03")
        assert resp.status_code == 404
