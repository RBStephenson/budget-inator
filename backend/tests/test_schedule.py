"""Integration tests for GET /schedule."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.models import Bill, PaySchedule
from app.models.pay_period_actual import PayPeriodActual

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_schedule(db, first_paycheck: date | None = None, net_salary: str = "1000.00"):
    sched = PaySchedule(
        net_salary=net_salary,
        first_paycheck_date=first_paycheck or date(2025, 1, 3),
        beginning_balance="500.00",
        frequency="biweekly",
    )
    db.add(sched)
    db.commit()
    return sched


def _make_monthly_bill(
    db, name: str = "Rent", amount: str = "800.00", due_day: int = 1
):
    bill = Bill(
        name=name,
        estimated_amount=amount,
        recurrence="monthly",
        due_day=due_day,
        first_due_date=None,
        grace_period_days=0,
        category="housing",
        is_variable=False,
        is_active=True,
    )
    db.add(bill)
    db.commit()
    return bill


def _make_one_time_bill(db, name: str, amount: str, due_date: date, grace: int = 0):
    bill = Bill(
        name=name,
        estimated_amount=amount,
        recurrence="one_time",
        due_day=None,
        first_due_date=due_date,
        grace_period_days=grace,
        category="other",
        is_variable=False,
        is_active=True,
    )
    db.add(bill)
    db.commit()
    return bill


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_pay_schedule_returns_404(client: TestClient):
    resp = client.get("/schedule")
    assert resp.status_code == 404
    assert "pay schedule" in resp.json()["detail"].lower()


def test_default_returns_4_periods(client: TestClient, db):
    _make_schedule(db, first_paycheck=date.today())
    resp = client.get("/schedule")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["period_count"] == 4
    assert len(body["periods"]) == 4


def test_default_first_period_contains_today(client: TestClient, db):
    # Use today as first paycheck so today is in period 0
    _make_schedule(db, first_paycheck=date.today())
    resp = client.get("/schedule")
    assert resp.status_code == 200
    periods = resp.json()["periods"]
    first = periods[0]
    today_str = date.today().isoformat()
    assert first["period_start"] <= today_str <= first["period_end"]


def test_periods_have_correct_structure(client: TestClient, db):
    _make_schedule(db)
    resp = client.get("/schedule")
    assert resp.status_code == 200
    period = resp.json()["periods"][0]
    for key in (
        "period_index",
        "pay_date",
        "original_pay_date",
        "is_overridden",
        "period_start",
        "period_end",
        "opening_balance",
        "total_bills",
        "remaining_balance",
        "flagged_bill_count",
        "assigned_bills",
    ):
        assert key in period, f"missing key: {key}"


def test_date_range_filters_periods(client: TestClient, db):
    # Biweekly from 2025-01-03: periods start 01-03, 01-17, 01-31, 02-14, ...
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    resp = client.get("/schedule?from=2025-01-03&to=2025-01-30")
    assert resp.status_code == 200
    body = resp.json()
    # Should cover the Jan-03 and Jan-17 periods (end Jan-16, Jan-30)
    assert body["summary"]["period_count"] == 2
    assert body["periods"][0]["period_start"] == "2025-01-03"
    assert body["periods"][1]["period_start"] == "2025-01-17"


def test_to_before_from_returns_422(client: TestClient, db):
    _make_schedule(db)
    resp = client.get("/schedule?from=2025-02-01&to=2025-01-01")
    assert resp.status_code == 422


def test_bills_assigned_to_correct_period(client: TestClient, db):
    # Biweekly starting 2025-01-03; period 0 = Jan 3–16, period 1 = Jan 17–30
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    # Monthly bill due on the 15th falls in period 0 (Jan 3–16)
    _make_monthly_bill(db, name="Internet", due_day=15)

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-30")
    assert resp.status_code == 200
    periods = resp.json()["periods"]
    p0_names = [b["name"] for b in periods[0]["assigned_bills"]]
    assert "Internet" in p0_names
    assert all(b["name"] != "Internet" for b in periods[1]["assigned_bills"])


def test_rolling_balance_carries_over(client: TestClient, db):
    # net_salary=1000, beginning_balance=500
    # period 0: opens with 1500, no bills → remaining 1500
    # period 1: opens with 1500 + 1000 = 2500
    _make_schedule(db, first_paycheck=date(2025, 1, 3), net_salary="1000.00")
    resp = client.get("/schedule?from=2025-01-03&to=2025-01-30")
    assert resp.status_code == 200
    periods = resp.json()["periods"]
    assert float(periods[0]["opening_balance"]) == pytest.approx(1500.0)
    assert float(periods[1]["opening_balance"]) == pytest.approx(2500.0)


def test_late_flagged_bill_in_summary(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    # one-time bill due 90 days before our window — should be late_flagged
    _make_one_time_bill(db, "Old Bill", "100.00", due_date=date(2024, 10, 1))

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_flagged_bills"] >= 1
    flagged = [
        b
        for p in body["periods"]
        for b in p["assigned_bills"]
        if b["status"] == "late_flagged"
    ]
    assert len(flagged) >= 1
    assert flagged[0]["name"] == "Old Bill"


def test_inactive_bills_excluded(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    _make_monthly_bill(db, name="ActiveBill", due_day=10)
    inactive = Bill(
        name="InactiveBill",
        estimated_amount="50.00",
        recurrence="monthly",
        due_day=10,
        first_due_date=None,
        grace_period_days=0,
        category="other",
        is_variable=False,
        is_active=False,
    )
    db.add(inactive)
    db.commit()

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-30")
    assert resp.status_code == 200
    all_bill_names = [
        b["name"] for p in resp.json()["periods"] for b in p["assigned_bills"]
    ]
    assert "ActiveBill" in all_bill_names
    assert "InactiveBill" not in all_bill_names


def test_only_from_date_defaults_to_to_same_day(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    resp = client.get("/schedule?from=2025-01-10")
    assert resp.status_code == 200
    # from=Jan10 with no to=: should return the single period containing Jan 10
    assert resp.json()["summary"]["period_count"] >= 1


def test_summary_totals_match_periods(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    _make_one_time_bill(db, "Late", "99.00", due_date=date(2024, 10, 1))  # flagged

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-30")
    assert resp.status_code == 200
    body = resp.json()
    manual_flagged = sum(
        1
        for p in body["periods"]
        for b in p["assigned_bills"]
        if b["status"] == "late_flagged"
    )
    assert body["summary"]["total_flagged_bills"] == manual_flagged


# ---------------------------------------------------------------------------
# Payment status overlay tests
# ---------------------------------------------------------------------------


def test_paid_bill_shows_paid_status(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    bill = _make_monthly_bill(db, name="Rent", amount="800.00", due_day=10)

    # Mark it paid via the bill-instances endpoint
    client.patch(
        f"/bill-instances/{bill.id}/2025-01-10",
        json={"status": "paid"},
    )

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    bills = resp.json()["periods"][0]["assigned_bills"]
    rent = next(b for b in bills if b["name"] == "Rent")
    assert rent["status"] == "paid"
    assert rent["instance_id"] is not None


def test_skipped_bill_excluded_from_total(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3), net_salary="1000.00")
    bill = _make_monthly_bill(db, name="Rent", amount="800.00", due_day=10)

    client.patch(
        f"/bill-instances/{bill.id}/2025-01-10",
        json={"status": "skipped"},
    )

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    period = resp.json()["periods"][0]
    assert float(period["total_bills"]) == pytest.approx(0.0)
    assert float(period["remaining_balance"]) == pytest.approx(1500.0)


def test_paid_with_actual_amount_uses_actual_in_total(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3), net_salary="1000.00")
    bill = _make_monthly_bill(db, name="Electric", amount="100.00", due_day=10)

    client.patch(
        f"/bill-instances/{bill.id}/2025-01-10",
        json={"status": "paid", "actual_amount": "75.00"},
    )

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    period = resp.json()["periods"][0]
    assert float(period["total_bills"]) == pytest.approx(75.0)
    electric = next(b for b in period["assigned_bills"] if b["name"] == "Electric")
    assert float(electric["actual_amount"]) == pytest.approx(75.0)


def test_no_instance_leaves_status_as_on_time(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    _make_monthly_bill(db, name="Rent", due_day=10)

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    bills = resp.json()["periods"][0]["assigned_bills"]
    rent = next(b for b in bills if b["name"] == "Rent")
    assert rent["status"] == "on_time"
    assert rent["instance_id"] is None


# ---------------------------------------------------------------------------
# Variable bill flag propagation tests
# ---------------------------------------------------------------------------


def test_variable_bill_flag_is_true_in_schedule(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    bill = Bill(
        name="Electric",
        estimated_amount="120.00",
        recurrence="monthly",
        due_day=10,
        first_due_date=None,
        grace_period_days=0,
        category="utilities",
        is_variable=True,
        is_active=True,
    )
    db.add(bill)
    db.commit()

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    bills = resp.json()["periods"][0]["assigned_bills"]
    electric = next(b for b in bills if b["name"] == "Electric")
    assert electric["is_variable"] is True


def test_non_variable_bill_flag_is_false_in_schedule(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    _make_monthly_bill(db, name="Rent", due_day=10)

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    bills = resp.json()["periods"][0]["assigned_bills"]
    rent = next(b for b in bills if b["name"] == "Rent")
    assert rent["is_variable"] is False


# ---------------------------------------------------------------------------
# Category propagation tests
# ---------------------------------------------------------------------------


def test_category_is_present_in_assigned_bill(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    _make_monthly_bill(db, name="Rent", due_day=10)

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    bills = resp.json()["periods"][0]["assigned_bills"]
    rent = next(b for b in bills if b["name"] == "Rent")
    assert rent["category"] == "housing"


def test_category_reflects_bill_category(client: TestClient, db):
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    bill = Bill(
        name="Netflix",
        estimated_amount="15.00",
        recurrence="monthly",
        due_day=10,
        first_due_date=None,
        grace_period_days=0,
        category="subscriptions",
        is_variable=False,
        is_active=True,
    )
    db.add(bill)
    db.commit()

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")
    assert resp.status_code == 200
    all_bills = [b for p in resp.json()["periods"] for b in p["assigned_bills"]]
    netflix = next(b for b in all_bills if b["name"] == "Netflix")
    assert netflix["category"] == "subscriptions"


def test_actual_balance_reanchors_schedule_opening(client: TestClient, db):
    """#55: a confirmed actual balance overrides the computed opening balance."""
    # begin 500 + salary 1000 → computed opening would be 1500
    _make_schedule(db, first_paycheck=date(2025, 1, 3))
    db.add(
        PayPeriodActual(
            pay_date=date(2025, 1, 3),
            actual_net_pay=None,
            actual_balance="2000.00",
        )
    )
    db.commit()

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-10")
    assert resp.status_code == 200
    periods = resp.json()["periods"]
    assert periods[0]["opening_balance"] == "2000.00"
