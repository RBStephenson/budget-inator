"""Integration tests for GET /schedule/monthly-summary."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.models import Bill, PaySchedule


def _make_schedule(
    db,
    first_paycheck: date,
    net_salary: str = "1000.00",
    frequency: str = "biweekly",
):
    sched = PaySchedule(
        net_salary=net_salary,
        first_paycheck_date=first_paycheck,
        beginning_balance="500.00",
        frequency=frequency,
    )
    db.add(sched)
    db.commit()
    return sched


def _make_bill(
    db,
    name: str = "Rent",
    amount: str = "800.00",
    recurrence: str = "monthly",
    due_day: int | None = 1,
    due_date: date | None = None,
    category: str = "housing",
    is_variable: bool = False,
):
    bill = Bill(
        name=name,
        estimated_amount=amount,
        recurrence=recurrence,
        due_day=due_day,
        first_due_date=due_date,
        grace_period_days=0,
        category=category,
        is_variable=is_variable,
        is_active=True,
    )
    db.add(bill)
    db.commit()
    return bill


class TestMonthlySummaryBasics:
    def test_returns_404_without_schedule(self, client: TestClient) -> None:
        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 404

    def test_returns_3_months_by_default(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary")
        assert r.status_code == 200
        assert len(r.json()["months"]) == 3

    def test_explicit_range_returns_correct_months(
        self, client: TestClient, db
    ) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-03")
        assert r.status_code == 200
        months = [m["month"] for m in r.json()["months"]]
        assert months == ["2025-01", "2025-02", "2025-03"]

    def test_single_month_range(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary?from=2025-06&to=2025-06")
        assert r.status_code == 200
        assert len(r.json()["months"]) == 1
        assert r.json()["months"][0]["month"] == "2025-06"

    def test_to_before_from_returns_422(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary?from=2025-06&to=2025-01")
        assert r.status_code == 422

    def test_invalid_month_format_returns_422(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary?from=jan-2025")
        assert r.status_code == 422

    def test_out_of_range_from_month_returns_422(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary?from=2025-13&to=2025-13")
        assert r.status_code == 422

    def test_zero_from_month_returns_422(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary?from=2025-00")
        assert r.status_code == 422

    def test_out_of_range_to_month_returns_422(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-99")
        assert r.status_code == 422

    def test_response_has_expected_fields(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        m = r.json()["months"][0]
        for key in ("month", "total_income", "total_bills", "available", "categories"):
            assert key in m


class TestMonthlySummaryIncome:
    def test_biweekly_two_periods_in_february(self, client: TestClient, db) -> None:
        # Biweekly from Jan 3: Feb paydays are Feb 14 and Feb 28 → 2 paychecks
        _make_schedule(db, first_paycheck=date(2025, 1, 3), net_salary="1000.00")
        r = client.get("/schedule/monthly-summary?from=2025-02&to=2025-02")
        assert r.status_code == 200
        total_income = float(r.json()["months"][0]["total_income"])
        assert total_income == pytest.approx(2000.0)

    def test_biweekly_three_periods_straddling_month(
        self, client: TestClient, db
    ) -> None:
        # Biweekly from Jan 3: Jan 3, Jan 17, Jan 31 all start in Jan → 3 paychecks
        _make_schedule(db, first_paycheck=date(2025, 1, 3), net_salary="500.00")
        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        total_income = float(r.json()["months"][0]["total_income"])
        assert total_income == pytest.approx(1500.0)

    def test_income_zero_when_no_payday_in_month(self, client: TestClient, db) -> None:
        # Monthly paycheck on Feb 1 → Jan has 0 income
        _make_schedule(
            db,
            first_paycheck=date(2025, 2, 1),
            net_salary="2000.00",
            frequency="monthly",
        )
        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        total_income = float(r.json()["months"][0]["total_income"])
        assert total_income == pytest.approx(0.0)


class TestMonthlySummaryBills:
    def test_monthly_bill_appears_in_correct_month(
        self, client: TestClient, db
    ) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        _make_bill(db, name="Rent", amount="900.00", due_day=15)

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-02")
        assert r.status_code == 200
        months = r.json()["months"]
        # Rent is due on the 15th every month
        assert float(months[0]["total_bills"]) == pytest.approx(900.0)
        assert float(months[1]["total_bills"]) == pytest.approx(900.0)

    def test_available_equals_income_minus_bills(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3), net_salary="1000.00")
        _make_bill(db, name="Rent", amount="500.00", due_day=10)

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        m = r.json()["months"][0]
        income = float(m["total_income"])
        bills = float(m["total_bills"])
        available = float(m["available"])
        assert available == pytest.approx(income - bills)

    def test_no_bills_gives_zero_total_bills(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/schedule/monthly-summary?from=2025-06&to=2025-06")
        assert r.status_code == 200
        assert float(r.json()["months"][0]["total_bills"]) == pytest.approx(0.0)

    def test_inactive_bills_excluded(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        active = _make_bill(db, name="Active", amount="100.00", due_day=10)
        inactive = Bill(
            name="Inactive",
            estimated_amount="200.00",
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

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        assert float(r.json()["months"][0]["total_bills"]) == pytest.approx(100.0)
        _ = active  # suppress unused warning


class TestMonthlySummaryCategories:
    def test_bills_grouped_by_category(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        _make_bill(db, name="Rent", amount="900.00", due_day=1, category="housing")
        _make_bill(
            db,
            name="Electric",
            amount="100.00",
            due_day=15,
            category="utilities",
        )

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        cats = {c["category"]: c for c in r.json()["months"][0]["categories"]}
        assert "housing" in cats
        assert "utilities" in cats
        assert float(cats["housing"]["subtotal"]) == pytest.approx(900.0)
        assert float(cats["utilities"]["subtotal"]) == pytest.approx(100.0)

    def test_categories_in_canonical_order(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        _make_bill(
            db, name="Netflix", amount="15.00", due_day=5, category="subscriptions"
        )
        _make_bill(
            db, name="Electric", amount="80.00", due_day=10, category="utilities"
        )
        _make_bill(db, name="Rent", amount="900.00", due_day=1, category="housing")

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        cat_names = [c["category"] for c in r.json()["months"][0]["categories"]]
        assert cat_names.index("housing") < cat_names.index("utilities")
        assert cat_names.index("utilities") < cat_names.index("subscriptions")

    def test_category_bills_sorted_by_due_date(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        _make_bill(db, name="LaterBill", amount="50.00", due_day=20, category="housing")
        _make_bill(
            db, name="EarlierBill", amount="50.00", due_day=5, category="housing"
        )

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        housing = next(
            c for c in r.json()["months"][0]["categories"] if c["category"] == "housing"
        )
        bill_names = [b["name"] for b in housing["bills"]]
        assert bill_names == ["EarlierBill", "LaterBill"]


class TestMonthlySummaryPaymentOverlay:
    """Skipped/paid status and actual amounts mirror the pay-period view."""

    def test_skipped_bill_excluded_from_total(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        bill = _make_bill(db, name="Rent", amount="800.00", due_day=10)
        client.patch(
            f"/bill-instances/{bill.id}/2025-01-10",
            json={"status": "skipped"},
        )

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        assert float(r.json()["months"][0]["total_bills"]) == pytest.approx(0.0)

    def test_skipped_bill_marked_in_item(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        bill = _make_bill(db, name="Rent", amount="800.00", due_day=10)
        client.patch(
            f"/bill-instances/{bill.id}/2025-01-10",
            json={"status": "skipped"},
        )

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        housing = r.json()["months"][0]["categories"][0]
        assert housing["bills"][0]["status"] == "skipped"
        # subtotal is also zero
        assert float(housing["subtotal"]) == pytest.approx(0.0)

    def test_paid_actual_amount_used_in_total(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        bill = _make_bill(db, name="Electric", amount="100.00", due_day=10)
        client.patch(
            f"/bill-instances/{bill.id}/2025-01-10",
            json={"status": "paid", "actual_amount": "75.00"},
        )

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        m = r.json()["months"][0]
        assert float(m["total_bills"]) == pytest.approx(75.0)
        item = m["categories"][0]["bills"][0]
        assert item["status"] == "paid"
        assert float(item["actual_amount"]) == pytest.approx(75.0)

    def test_unpaid_bill_uses_estimated_amount(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        _make_bill(db, name="Rent", amount="800.00", due_day=10)

        r = client.get("/schedule/monthly-summary?from=2025-01&to=2025-01")
        assert r.status_code == 200
        m = r.json()["months"][0]
        assert float(m["total_bills"]) == pytest.approx(800.0)
        item = m["categories"][0]["bills"][0]
        assert item["status"] == "on_time"
        assert item["actual_amount"] is None
