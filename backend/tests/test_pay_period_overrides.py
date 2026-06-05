"""Tests for pay-period-overrides API and schedule override reflection."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.models import PaySchedule


def _make_schedule(db) -> None:
    db.add(
        PaySchedule(
            net_salary="1000.00",
            first_paycheck_date=date(2025, 1, 3),
            beginning_balance="0.00",
            frequency="biweekly",
        )
    )
    db.commit()


class TestUpsertOverride:
    def test_creates_override(self, client: TestClient, db):
        resp = client.put(
            "/pay-period-overrides/2025-01-03",
            json={"override_date": "2025-01-02"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["original_pay_date"] == "2025-01-03"
        assert data["overridden_pay_date"] == "2025-01-02"

    def test_updates_existing_override(self, client: TestClient, db):
        client.put(
            "/pay-period-overrides/2025-01-03",
            json={"override_date": "2025-01-02"},
        )
        resp = client.put(
            "/pay-period-overrides/2025-01-03",
            json={"override_date": "2025-01-01"},
        )
        assert resp.status_code == 200
        assert resp.json()["overridden_pay_date"] == "2025-01-01"

    def test_rejects_same_date(self, client: TestClient, db):
        resp = client.put(
            "/pay-period-overrides/2025-01-03",
            json={"override_date": "2025-01-03"},
        )
        assert resp.status_code == 422

    def test_accepts_future_date(self, client: TestClient, db):
        resp = client.put(
            "/pay-period-overrides/2025-01-03",
            json={"override_date": "2025-01-04"},
        )
        assert resp.status_code == 200


class TestDeleteOverride:
    def test_deletes_existing_override(self, client: TestClient, db):
        client.put(
            "/pay-period-overrides/2025-01-03",
            json={"override_date": "2025-01-02"},
        )
        resp = client.delete("/pay-period-overrides/2025-01-03")
        assert resp.status_code == 204

    def test_returns_404_if_not_found(self, client: TestClient):
        resp = client.delete("/pay-period-overrides/2025-01-03")
        assert resp.status_code == 404


class TestScheduleReflectsOverride:
    def test_pay_date_overridden_in_schedule(self, client: TestClient, db):
        _make_schedule(db)
        # Period 0 starts/pays Jan 3
        client.put(
            "/pay-period-overrides/2025-01-03",
            json={"override_date": "2025-01-02"},
        )
        resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
        assert resp.status_code == 200
        p = resp.json()["periods"][0]
        assert p["pay_date"] == "2025-01-02"
        assert p["original_pay_date"] == "2025-01-03"
        assert p["is_overridden"] is True

    def test_non_overridden_period_shows_computed_date(self, client: TestClient, db):
        _make_schedule(db)
        resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
        assert resp.status_code == 200
        p = resp.json()["periods"][0]
        assert p["pay_date"] == "2025-01-03"
        assert p["original_pay_date"] == "2025-01-03"
        assert p["is_overridden"] is False

    def test_override_only_affects_its_period(self, client: TestClient, db):
        _make_schedule(db)
        client.put(
            "/pay-period-overrides/2025-01-03",
            json={"override_date": "2025-01-02"},
        )
        resp = client.get("/schedule?from=2025-01-03&to=2025-01-30")
        assert resp.status_code == 200
        periods = resp.json()["periods"]
        assert periods[0]["is_overridden"] is True
        assert periods[1]["is_overridden"] is False

    def test_deleted_override_reverts_to_computed(self, client: TestClient, db):
        _make_schedule(db)
        client.put(
            "/pay-period-overrides/2025-01-03",
            json={"override_date": "2025-01-02"},
        )
        client.delete("/pay-period-overrides/2025-01-03")
        resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
        assert resp.status_code == 200
        p = resp.json()["periods"][0]
        assert p["pay_date"] == "2025-01-03"
        assert p["is_overridden"] is False
