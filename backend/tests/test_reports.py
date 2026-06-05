"""Tests for the budget PDF report endpoint and rendering service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.models import Bill, BillInstance, PaySchedule
from app.services.pdf_report import _make_footer, _money, render_budget_pdf
from app.services.report_service import build_report_data


class _FakeCanvas:
    """Records text drawn by the footer callback."""

    def __init__(self) -> None:
        self.texts: list[str] = []

    def saveState(self) -> None:  # noqa: N802 (reportlab API name)
        pass

    def restoreState(self) -> None:  # noqa: N802
        pass

    def setFont(self, *a) -> None:  # noqa: N802
        pass

    def setFillColor(self, *a) -> None:  # noqa: N802
        pass

    def drawString(self, x, y, text) -> None:  # noqa: N802
        self.texts.append(text)

    def drawRightString(self, x, y, text) -> None:  # noqa: N802
        self.texts.append(text)


class _FakeDoc:
    def __init__(self, page: int) -> None:
        self.page = page


def _make_schedule(db, first_paycheck: date = date(2025, 1, 3)):
    sched = PaySchedule(
        net_salary="1000.00",
        first_paycheck_date=first_paycheck,
        beginning_balance="500.00",
        frequency="biweekly",
    )
    db.add(sched)
    db.commit()
    return sched


def _make_bill(
    db,
    name: str = "Rent",
    amount: str = "800.00",
    recurrence: str = "monthly",
    due_day: int | None = 10,
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


class TestBudgetPdfEndpoint:
    def test_returns_pdf_bytes(self, client: TestClient, db) -> None:
        _make_schedule(db)
        _make_bill(db, name="Rent", due_day=10)

        r = client.get("/reports/budget.pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 1000

    def test_content_disposition_filename(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date.today())
        r = client.get("/reports/budget.pdf")
        assert r.status_code == 200
        disp = r.headers["content-disposition"]
        assert "attachment" in disp
        assert disp.endswith('.pdf"')
        assert "budget-" in disp

    def test_filename_uses_report_start_date(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        r = client.get("/reports/budget.pdf?from=2025-01-03&to=2025-01-30")
        assert r.status_code == 200
        assert 'filename="budget-2025-01-03.pdf"' in r.headers["content-disposition"]

    def test_generates_with_no_bills(self, client: TestClient, db) -> None:
        _make_schedule(db)
        r = client.get("/reports/budget.pdf")
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"

    def test_returns_404_without_schedule(self, client: TestClient, db) -> None:
        r = client.get("/reports/budget.pdf")
        assert r.status_code == 404


class TestReportData:
    def test_includes_schedule_bills_and_monthly(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        _make_bill(db, name="Rent", amount="800.00", due_day=10)

        report = build_report_data(db, date(2025, 1, 3), date(2025, 1, 30))
        assert len(report.schedule.periods) >= 1
        assert len(report.bill_list) == 1
        assert report.bill_list[0].name == "Rent"
        assert len(report.monthly.months) >= 1

    def test_default_range_returns_six_periods(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date.today())
        report = build_report_data(db)
        assert len(report.schedule.periods) == 6

    def test_bill_list_sorted_alphabetically(self, client: TestClient, db) -> None:
        _make_schedule(db)
        _make_bill(db, name="Zebra", due_day=5, category="other")
        _make_bill(db, name="Apple", due_day=6, category="other")

        report = build_report_data(db)
        names = [b.name for b in report.bill_list]
        assert names == ["Apple", "Zebra"]

    def test_annual_cost_for_monthly_bill(self, client: TestClient, db) -> None:
        _make_schedule(db)
        _make_bill(db, name="Rent", amount="100.00", recurrence="monthly", due_day=10)
        report = build_report_data(db)
        rent = next(b for b in report.bill_list if b.name == "Rent")
        assert rent.annual_cost == 1200  # 100 * 12

    def test_annual_cost_for_biweekly_bill(self, client: TestClient, db) -> None:
        _make_schedule(db)
        _make_bill(
            db,
            name="Insurance",
            amount="50.00",
            recurrence="biweekly",
            due_day=None,
            due_date=date(2025, 1, 10),
            category="insurance",
        )
        report = build_report_data(db)
        ins = next(b for b in report.bill_list if b.name == "Insurance")
        assert ins.annual_cost == 1300  # 50 * 26


class TestPdfRendering:
    def test_render_returns_valid_pdf(self, client: TestClient, db) -> None:
        _make_schedule(db)
        _make_bill(db, name="Rent", due_day=10)
        report = build_report_data(db)
        pdf = render_budget_pdf(report)
        assert pdf[:5] == b"%PDF-"
        assert b"%%EOF" in pdf[-1024:]

    def test_render_with_late_flagged_bill(self, client: TestClient, db) -> None:
        # One-time bill due well before the window → late_flagged
        _make_schedule(db, first_paycheck=date.today())
        _make_bill(
            db,
            name="OldBill",
            amount="60.00",
            recurrence="one_time",
            due_day=None,
            due_date=date.today().replace(year=date.today().year - 1),
            category="other",
        )
        report = build_report_data(db)
        # at least one late-flagged bill present in the projected schedule
        statuses = [b.status for p in report.schedule.periods for b in p.assigned_bills]
        assert "late_flagged" in statuses
        pdf = render_budget_pdf(report)
        assert pdf[:5] == b"%PDF-"

    def test_render_reflects_paid_actual_amount(self, client: TestClient, db) -> None:
        _make_schedule(db, first_paycheck=date(2025, 1, 3))
        bill = _make_bill(db, name="Electric", amount="100.00", due_day=10)
        inst = BillInstance(
            bill_id=bill.id,
            due_date=date(2025, 1, 10),
            estimated_amount="100.00",
            status="paid",
            actual_amount="75.00",
        )
        db.add(inst)
        db.commit()

        report = build_report_data(db, date(2025, 1, 3), date(2025, 1, 16))
        electric = next(
            b
            for p in report.schedule.periods
            for b in p.assigned_bills
            if b.name == "Electric"
        )
        assert electric.status == "paid"
        assert str(electric.actual_amount) == "75.00"
        pdf = render_budget_pdf(report)
        assert pdf[:5] == b"%PDF-"


class TestMoneyFormat:
    def test_positive_amount(self) -> None:
        assert _money(Decimal("1200.5")) == "$1,200.50"

    def test_zero(self) -> None:
        assert _money(Decimal("0")) == "$0.00"

    def test_negative_puts_sign_before_dollar(self) -> None:
        # Overspent balances read "-$50.00", not "$-50.00"
        assert _money(Decimal("-50.00")) == "-$50.00"


class TestFooter:
    def test_footer_draws_generated_date_and_page_number(self) -> None:
        footer = _make_footer(date(2025, 1, 3), margin=43.2)
        canvas = _FakeCanvas()
        footer(canvas, _FakeDoc(page=1))
        assert "Generated on Jan 3, 2025" in canvas.texts
        assert "Page 1" in canvas.texts

    def test_footer_reflects_current_page(self) -> None:
        footer = _make_footer(date(2025, 1, 3), margin=43.2)
        canvas = _FakeCanvas()
        footer(canvas, _FakeDoc(page=3))
        assert "Page 3" in canvas.texts
