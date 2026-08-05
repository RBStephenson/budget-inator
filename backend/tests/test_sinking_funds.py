"""Regression tests for sinking-fund projections (#126)."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.models import Bill, PaySchedule


def _make_schedule(db) -> None:
    db.add(
        PaySchedule(
            net_salary="1000.00",
            first_paycheck_date=date(2025, 1, 3),
            beginning_balance="500.00",
            frequency="biweekly",
        )
    )
    db.commit()


def _make_annual_bill(db) -> Bill:
    bill = Bill(
        name="Insurance",
        estimated_amount="1200.00",
        recurrence="annual",
        due_day=None,
        first_due_date=date(2025, 3, 1),
        grace_period_days=0,
        category="insurance",
        is_variable=False,
        sinking_fund_enabled=True,
        is_active=True,
    )
    db.add(bill)
    db.commit()
    return bill


def _make_annual_bill_via_api(client: TestClient) -> None:
    """Create the bill through the real endpoint, which always writes a
    ``BillVersion`` row (see ``create_bill``). Bills built by directly
    inserting a ``Bill`` row (``_make_annual_bill``) skip that and take a
    different, unversioned code path in ``bill_inputs_for_window`` - no real
    bill in the app is ever unversioned, so tests should exercise this path.
    """
    resp = client.post(
        "/bills",
        json={
            "name": "Insurance",
            "amount": "1200.00",
            "recurrence": "annual",
            "due_date": "2025-03-01",
            "grace_period_days": 0,
            "category": "insurance",
            "is_variable": False,
            "sinking_fund_enabled": True,
        },
    )
    assert resp.status_code == 201


def test_sinking_fund_reduces_safe_to_spend(client: TestClient, db) -> None:
    _make_schedule(db)
    _make_annual_bill_via_api(client)

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")

    assert resp.status_code == 200
    period = resp.json()["periods"][0]
    assert period["total_bills"] == "0"
    assert float(period["total_sinking_funds"]) > 0
    assert float(period["remaining_balance"]) < 1500.0
    fund = period["sinking_fund_contributions"][0]
    assert fund["name"] == "Insurance"
    assert fund["next_due_date"] == "2025-03-01"
    assert fund["target_amount"] == "1200.00"


def test_due_occurrence_uses_reserved_balance_and_shows_shortfall(
    client: TestClient, db
) -> None:
    _make_schedule(db)
    _make_annual_bill_via_api(client)

    resp = client.get("/schedule?from=2025-01-03&to=2025-03-13")

    assert resp.status_code == 200
    bills = [b for p in resp.json()["periods"] for b in p["assigned_bills"]]
    insurance = next(b for b in bills if b["name"] == "Insurance")
    assert insurance["amount"] == "1200.00"
    assert float(insurance["sinking_fund_applied"]) > 0
    assert float(insurance["sinking_fund_shortfall"]) >= 0


def test_monthly_summary_includes_sinking_fund_reserves(client: TestClient, db) -> None:
    _make_schedule(db)
    _make_annual_bill_via_api(client)

    resp = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")

    assert resp.status_code == 200
    month = resp.json()["months"][0]
    assert float(month["total_sinking_funds"]) > 0
    assert float(month["available"]) == pytest.approx(
        float(month["total_income"])
        - float(month["total_bills"])
        - float(month["total_sinking_funds"])
    )


def test_default_schedule_query_still_contributes_for_api_created_bill(
    client: TestClient, db
) -> None:
    """Regression test: bill_inputs_for_window used to clamp a bill's only
    (current) version's active_end to the projection window, so the
    sinking-fund lookahead (370 days past that window) could never see a
    future due date and contributions were silently zero - but only for bills
    with a real BillVersion row, i.e. every bill actually created through the
    app. Uses the default (unbounded from/to) /schedule query, matching how
    the dashboard calls it.
    """
    _make_schedule(db)
    _make_annual_bill_via_api(client)

    resp = client.get("/schedule")

    assert resp.status_code == 200
    period = resp.json()["periods"][0]
    assert float(period["total_sinking_funds"]) > 0
    assert period["sinking_fund_contributions"][0]["name"] == "Insurance"


def test_export_import_preserves_sinking_fund_flag(client: TestClient, db) -> None:
    _make_annual_bill(db)

    backup = client.get("/data/export").json()
    assert backup["version"] == 7
    assert backup["bills"][0]["sinking_fund_enabled"] is True
    assert backup["bill_versions"][0]["sinking_fund_enabled"] is True

    assert client.delete("/data").status_code == 204
    assert client.post("/data/import", json=backup).status_code == 204
    restored = client.get("/data/export").json()
    assert restored["bills"][0]["sinking_fund_enabled"] is True
