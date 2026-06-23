"""Regression tests for effective-dated bill history (#130)."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.models import Bill, BillVersion, PaySchedule


def _make_schedule(db) -> None:
    db.add(
        PaySchedule(
            net_salary="2000.00",
            first_paycheck_date=date(2025, 1, 3),
            beginning_balance="500.00",
            frequency="biweekly",
        )
    )
    db.commit()


def _create_rent(client: TestClient) -> dict:
    resp = client.post(
        "/bills",
        json={
            "name": "Rent",
            "amount": "800.00",
            "recurrence": "monthly",
            "due_day": 10,
            "grace_period_days": 0,
            "category": "housing",
            "is_variable": False,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_patch_creates_effective_dated_version(client: TestClient, db) -> None:
    bill = _create_rent(client)

    resp = client.patch(
        f"/bills/{bill['id']}",
        json={
            "effective_date": "2025-02-01",
            "name": "Apartment Rent",
            "amount": "900.00",
        },
    )

    assert resp.status_code == 200
    versions = (
        db.query(BillVersion)
        .filter(BillVersion.bill_id == bill["id"])
        .order_by(BillVersion.effective_date)
        .all()
    )
    assert [(v.effective_date, v.name, str(v.estimated_amount)) for v in versions] == [
        (date(1, 1, 1), "Rent", "800.00"),
        (date(2025, 2, 1), "Apartment Rent", "900.00"),
    ]


def test_effective_dated_edit_does_not_rewrite_past_schedule(
    client: TestClient, db
) -> None:
    _make_schedule(db)
    bill = _create_rent(client)

    before = client.get("/schedule?from=2025-01-03&to=2025-02-13").json()
    jan_before = before["periods"][0]["assigned_bills"][0]
    feb_before = before["periods"][2]["assigned_bills"][0]
    assert jan_before["name"] == "Rent"
    assert jan_before["amount"] == "800.00"
    assert feb_before["amount"] == "800.00"

    resp = client.patch(
        f"/bills/{bill['id']}",
        json={
            "effective_date": "2025-02-01",
            "name": "Apartment Rent",
            "amount": "900.00",
            "category": "other",
        },
    )
    assert resp.status_code == 200

    after = client.get("/schedule?from=2025-01-03&to=2025-02-13").json()
    jan_after = after["periods"][0]["assigned_bills"][0]
    feb_after = after["periods"][2]["assigned_bills"][0]

    assert jan_after["name"] == "Rent"
    assert jan_after["amount"] == "800.00"
    assert jan_after["category"] == "housing"
    assert feb_after["name"] == "Apartment Rent"
    assert feb_after["amount"] == "900.00"
    assert feb_after["category"] == "other"
    assert float(after["periods"][0]["total_bills"]) == pytest.approx(800.0)
    assert float(after["periods"][2]["total_bills"]) == pytest.approx(900.0)


def test_monthly_summary_uses_historical_terms(client: TestClient, db) -> None:
    _make_schedule(db)
    bill = _create_rent(client)
    assert (
        client.patch(
            f"/bills/{bill['id']}",
            json={
                "effective_date": "2025-02-01",
                "name": "Apartment Rent",
                "amount": "900.00",
                "category": "other",
            },
        ).status_code
        == 200
    )

    resp = client.get("/schedule/monthly-summary?from=2025-01&to=2025-02")
    assert resp.status_code == 200
    jan, feb = resp.json()["months"]

    assert jan["total_bills"] == "800.00"
    assert jan["categories"][0]["category"] == "housing"
    assert jan["categories"][0]["bills"][0]["name"] == "Rent"
    assert feb["total_bills"] == "900.00"
    assert feb["categories"][0]["category"] == "other"
    assert feb["categories"][0]["bills"][0]["name"] == "Apartment Rent"


def test_instance_created_after_edit_uses_due_date_version(
    client: TestClient, db
) -> None:
    bill = _create_rent(client)
    assert (
        client.patch(
            f"/bills/{bill['id']}",
            json={"effective_date": "2025-02-01", "amount": "900.00"},
        ).status_code
        == 200
    )

    jan = client.patch(
        f"/bill-instances/{bill['id']}/2025-01-10",
        json={"status": "paid"},
    )
    feb = client.patch(
        f"/bill-instances/{bill['id']}/2025-02-10",
        json={"status": "paid"},
    )

    assert jan.status_code == 200
    assert feb.status_code == 200
    assert jan.json()["estimated_amount"] == "800.00"
    assert feb.json()["estimated_amount"] == "900.00"


def test_export_import_round_trip_preserves_bill_versions(
    client: TestClient, db
) -> None:
    bill = _create_rent(client)
    assert (
        client.patch(
            f"/bills/{bill['id']}",
            json={"effective_date": "2025-02-01", "amount": "900.00"},
        ).status_code
        == 200
    )

    backup = client.get("/data/export").json()
    assert backup["version"] == 6
    assert len(backup["bill_versions"]) == 2

    assert client.delete("/data").status_code == 204
    assert db.query(Bill).count() == 0

    resp = client.post("/data/import", json=backup)
    assert resp.status_code == 204
    restored_versions = db.query(BillVersion).order_by(BillVersion.effective_date).all()
    assert [str(v.estimated_amount) for v in restored_versions] == ["800.00", "900.00"]


def test_legacy_import_backfills_baseline_version(client: TestClient, db) -> None:
    payload = {
        "version": 4,
        "bills": [
            {
                "name": "Internet",
                "amount": "60.00",
                "recurrence": "monthly",
                "due_day": 5,
                "due_day_is_month_end": False,
                "category": "utilities",
            }
        ],
    }

    assert client.post("/data/import", json=payload).status_code == 204
    version = db.query(BillVersion).one()
    assert version.effective_date == date(1, 1, 1)
    assert version.name == "Internet"
    assert str(version.estimated_amount) == "60.00"


def test_delete_is_effective_dated_for_historical_windows(
    client: TestClient, db
) -> None:
    _make_schedule(db)
    bill = _create_rent(client)

    deleted = client.delete(f"/bills/{bill['id']}")
    assert deleted.status_code == 204

    old_window = client.get("/schedule?from=2025-01-03&to=2025-01-16").json()
    old_names = [
        item["name"]
        for period in old_window["periods"]
        for item in period["assigned_bills"]
    ]
    assert "Rent" in old_names


def test_direct_legacy_bill_without_versions_still_projects(
    client: TestClient, db
) -> None:
    _make_schedule(db)
    db.add(
        Bill(
            name="Legacy",
            estimated_amount="50.00",
            recurrence="monthly",
            due_day=10,
            first_due_date=None,
            grace_period_days=0,
            category="other",
            is_variable=False,
            is_active=True,
        )
    )
    db.commit()

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    names = [b["name"] for p in resp.json()["periods"] for b in p["assigned_bills"]]
    assert names == ["Legacy"]
