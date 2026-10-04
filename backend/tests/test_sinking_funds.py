"""Regression tests for sinking-fund projections (#126)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models import Bill, PaySchedule
from app.models.enums import BillRecurrence, PayFrequency
from app.services.pay_period_engine import (
    BillInput,
    apply_sinking_funds,
    build_periods,
    project,
)


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


def test_monthly_summary_does_not_double_count_sinking_fund_due_month(
    client: TestClient, db
) -> None:
    """Regression test: the monthly-summary view used to charge a
    sinking-fund bill's full amount in its due month AND its accumulated
    contributions in every prior month, double-counting the same bill. The
    pay-period view already nets this correctly (effective amount is the
    shortfall left after the reserve, 0 when fully funded) via
    assigned_bill_effective_amount - the monthly view must charge the same
    occurrence the same way.
    """
    _make_schedule(db)
    _make_annual_bill_via_api(client)

    summary = client.get("/schedule/monthly-summary?from=2025-01&to=2025-04").json()
    march = next(m for m in summary["months"] if m["month"] == "2025-03")

    schedule = client.get("/schedule?from=2025-01-03&to=2025-03-13").json()
    bills = [b for p in schedule["periods"] for b in p["assigned_bills"]]
    insurance = next(b for b in bills if b["name"] == "Insurance")
    expected_charge = Decimal(insurance["sinking_fund_shortfall"])

    # Not the full $1200 - it must already be reduced by the sinking-fund
    # reserve, matching the pay-period view for the same occurrence.
    assert Decimal(march["total_bills"]) == expected_charge
    assert expected_charge < Decimal("1200.00")


def test_contribution_amount_quantized_to_cents(client: TestClient, db) -> None:
    """Regression test: needed / funding_period_count can produce a
    repeating decimal (e.g. 100/3), and nothing quantized it before it fed
    reserves/saved_amount/shortfall_amount for every later period. A one-time
    $100 bill split over exactly 3 funding periods reproduces this: contribution
    must be a clean 2-decimal string, not a 28-digit repeating value.
    """
    _make_schedule(db)
    resp = client.post(
        "/bills",
        json={
            "name": "Repeating Decimal Test",
            "amount": "100.00",
            "recurrence": "one_time",
            "due_date": "2025-02-20",
            "grace_period_days": 0,
            "category": "other",
            "is_variable": False,
            "sinking_fund_enabled": True,
        },
    )
    assert resp.status_code == 201

    resp = client.get("/schedule?from=2025-01-03&to=2025-01-16")

    assert resp.status_code == 200
    period = resp.json()["periods"][0]
    fund = period["sinking_fund_contributions"][0]
    assert fund["contribution_amount"] == "33.33"
    assert fund["saved_amount"] == "33.33"


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


# ---------------------------------------------------------------------------
# BI-59: a bill with several versions is one fund, not one fund per version
# ---------------------------------------------------------------------------
#
# Fixed dates: biweekly pay from 2025-01-03, monthly "Water" due on the 20th,
# $100 until 2025-02-28 and $80 from 2025-03-01. Only the first five periods
# are pinned: the last periods of a projection under-count funding periods
# (review finding M1), and that fix must not have to rewrite these asserts.


def _water_version(
    amount: str, start: date, end: date | None, *, sinking: bool = True
) -> BillInput:
    return BillInput(
        id=1,
        name="Water",
        amount=Decimal(amount),
        recurrence=BillRecurrence.monthly,
        due_day=20,
        first_due_date=None,
        sinking_fund_enabled=sinking,
        active_start=start,
        active_end=end,
    )


def _project_water(versions: list[BillInput]):
    return project(
        date(2025, 1, 3),
        PayFrequency.biweekly,
        12,
        Decimal("2000"),
        Decimal("0"),
        versions,
    )


def test_versioned_sinking_bill_contributes_once_per_period_toward_real_due_date() -> (
    None
):
    periods = _project_water(
        [
            _water_version("100", date(2025, 1, 3), date(2025, 2, 28)),
            _water_version("80", date(2025, 3, 1), None),
        ]
    )

    assert all(len(p.sinking_fund_contributions) == 1 for p in periods)
    pinned = [
        (
            c.next_due_date,
            str(c.target_amount),
            str(c.contribution_amount),
            str(c.saved_amount),
        )
        for p in periods[:5]
        for c in p.sinking_fund_contributions
    ]
    assert pinned == [
        (date(2025, 1, 20), "100", "100.00", "100.00"),
        (date(2025, 2, 20), "100", "50.00", "50.00"),
        (date(2025, 2, 20), "100", "50.00", "100.00"),
        (date(2025, 3, 20), "80", "40.00", "40.00"),
        (date(2025, 3, 20), "80", "40.00", "80.00"),
    ]


def test_sinking_enabled_only_in_later_version_funds_only_its_due_dates() -> None:
    periods = _project_water(
        [
            _water_version("100", date(2025, 1, 3), date(2025, 2, 28), sinking=False),
            _water_version("80", date(2025, 3, 1), None),
        ]
    )

    assert all(len(p.sinking_fund_contributions) == 1 for p in periods)
    targets = {
        (c.next_due_date, str(c.target_amount))
        for p in periods
        for c in p.sinking_fund_contributions
    }
    assert all(due >= date(2025, 3, 20) and amount == "80" for due, amount in targets)


def _occurrence_funding(periods) -> dict[date, tuple[str, str]]:
    return {
        a.due_date: (str(a.sinking_fund_applied), str(a.sinking_fund_shortfall))
        for p in periods
        for a in p.assigned_bills
    }


def _saved_by_period_end(periods) -> list[tuple[date, str, str]]:
    return [
        (p.period_end, str(c.contribution_amount), str(c.saved_amount))
        for p in periods
        for c in p.sinking_fund_contributions
    ]


def test_non_sinking_occurrences_do_not_spend_a_later_versions_reserve() -> None:
    """BI-60 repro A: sinking turned on in a later version."""
    periods = _project_water(
        [
            _water_version("100", date(2025, 1, 3), date(2025, 2, 28), sinking=False),
            _water_version("80", date(2025, 3, 1), None),
        ]
    )

    funding = _occurrence_funding(periods)
    assert funding[date(2025, 1, 20)] == ("0", "0")
    assert funding[date(2025, 2, 20)] == ("0", "0")
    assert funding[date(2025, 3, 20)] == ("80.00", "0")
    assert _saved_by_period_end(periods)[:5] == [
        (date(2025, 1, 16), "16.00", "16.00"),
        (date(2025, 1, 30), "16.00", "32.00"),
        (date(2025, 2, 13), "16.00", "48.00"),
        (date(2025, 2, 27), "16.00", "64.00"),
        (date(2025, 3, 13), "16.00", "80.00"),
    ]


def test_turning_sinking_on_via_api_does_not_drain_the_fund_early(
    client: TestClient, db
) -> None:
    """BI-60 repro A through the real edit path: PATCH writes a new version."""
    _make_schedule(db)
    created = client.post(
        "/bills",
        json={
            "name": "Water",
            "amount": "100.00",
            "recurrence": "monthly",
            "due_day": 20,
            "category": "utilities",
            "sinking_fund_enabled": False,
        },
    ).json()
    resp = client.patch(
        f"/bills/{created['id']}",
        json={
            "amount": "80.00",
            "sinking_fund_enabled": True,
            "effective_date": "2025-03-01",
        },
    )
    assert resp.status_code == 200

    periods = client.get("/schedule?from=2025-01-03&to=2025-04-10").json()["periods"]

    funding = {
        b["due_date"]: (b["sinking_fund_applied"], b["sinking_fund_shortfall"])
        for p in periods
        for b in p["assigned_bills"]
    }
    assert funding["2025-01-20"] == ("0", "0")
    assert funding["2025-02-20"] == ("0", "0")
    assert funding["2025-03-20"] == ("80.00", "0")


def test_occurrences_after_sinking_is_turned_off_report_no_shortfall() -> None:
    """BI-60 repro B: sinking turned off in a later version."""
    periods = _project_water(
        [
            _water_version("100", date(2025, 1, 3), date(2025, 2, 28)),
            _water_version("80", date(2025, 3, 1), None, sinking=False),
        ]
    )

    funding = _occurrence_funding(periods)
    assert funding[date(2025, 1, 20)] == ("100.00", "0")
    assert funding[date(2025, 2, 20)] == ("100.00", "0")
    for due in (date(2025, 3, 20), date(2025, 4, 20), date(2025, 5, 20)):
        assert funding[due] == ("0", "0")


def test_leftover_reserve_stays_reserved_until_sinking_resumes() -> None:
    """Brent's call on BI-60: a reserve left over when sinking is turned off
    is neither spent nor released; a later sinking version picks it up."""
    periods = project(
        date(2025, 1, 3),
        PayFrequency.biweekly,
        12,
        Decimal("2000"),
        Decimal("0"),
        [
            _water_version("100", date(2025, 1, 3), date(2025, 2, 28)),
            _water_version("80", date(2025, 3, 1), date(2025, 4, 30), sinking=False),
            _water_version("90", date(2025, 5, 1), None),
        ],
        actual_amounts={(1, date(2025, 2, 20)): Decimal("60")},
    )

    funding = _occurrence_funding(periods)
    # Paying 60 against a 100 reserve leaves 40 behind.
    assert funding[date(2025, 2, 20)] == ("60", "0")
    assert funding[date(2025, 3, 20)] == ("0", "0")
    assert funding[date(2025, 4, 20)] == ("0", "0")
    assert funding[date(2025, 5, 20)] == ("90.00", "0")
    # The 40 carries forward: the May fund starts from 40, not from zero.
    assert _saved_by_period_end(periods)[3:9] == [
        (date(2025, 2, 27), "8.33", "48.33"),
        (date(2025, 3, 13), "8.33", "56.66"),
        (date(2025, 3, 27), "8.34", "65.00"),
        (date(2025, 4, 10), "8.33", "73.33"),
        (date(2025, 4, 24), "8.34", "81.67"),
        (date(2025, 5, 8), "8.33", "90.00"),
    ]


def test_versioned_sinking_bill_via_api_shows_one_row_per_period(
    client: TestClient, db
) -> None:
    _make_schedule(db)
    created = client.post(
        "/bills",
        json={
            "name": "Water",
            "amount": "100.00",
            "recurrence": "monthly",
            "due_day": 20,
            "category": "utilities",
            "sinking_fund_enabled": True,
        },
    ).json()
    resp = client.patch(
        f"/bills/{created['id']}",
        json={"amount": "80.00", "effective_date": "2025-03-01"},
    )
    assert resp.status_code == 200

    periods = client.get("/schedule?from=2025-01-03&to=2025-04-10").json()["periods"]

    rows = [p["sinking_fund_contributions"] for p in periods]
    assert all(len(r) == 1 for r in rows)
    assert [(r[0]["next_due_date"], r[0]["target_amount"]) for r in rows[:5]] == [
        ("2025-01-20", "100.00"),
        ("2025-02-20", "100.00"),
        ("2025-02-20", "100.00"),
        ("2025-03-20", "80.00"),
        ("2025-03-20", "80.00"),
    ]


# ---------------------------------------------------------------------------
# BI-61: the reserve is split over every paycheck before the due date, not just
# the paychecks this particular projection happened to generate
# ---------------------------------------------------------------------------


def _annual_sinking(amount: str, due: date) -> BillInput:
    return BillInput(
        id=7,
        name="Insurance",
        amount=Decimal(amount),
        recurrence=BillRecurrence.annual,
        due_day=None,
        first_due_date=due,
        sinking_fund_enabled=True,
    )


def _first_contribution(
    first_paycheck: date, frequency: PayFrequency, num_periods: int, bill: BillInput
) -> str:
    periods = project(
        first_paycheck, frequency, num_periods, Decimal("2000"), Decimal("0"), [bill]
    )
    return str(periods[0].sinking_fund_contributions[0].contribution_amount)


@pytest.mark.parametrize(
    ("first_paycheck", "frequency", "due", "expected"),
    [
        # Biweekly from 01-03: periods end 01-16 + 14k; 23 end before 12-01.
        (date(2025, 1, 3), PayFrequency.biweekly, date(2025, 12, 1), "52.17"),
        # Monthly anchored on the 31st: ends Feb 27 .. Nov 29 = 10 paychecks.
        (date(2025, 1, 31), PayFrequency.monthly, date(2025, 12, 15), "120.00"),
        # Semimonthly 15th/month-end: ends 2/14, 2/27, 3/14, 3/30, 4/14, 4/29.
        (date(2025, 1, 31), PayFrequency.semimonthly, date(2025, 4, 30), "200.00"),
    ],
)
def test_contribution_counts_paychecks_past_the_projection_end(
    first_paycheck: date, frequency: PayFrequency, due: date, expected: str
) -> None:
    bill = _annual_sinking("1200", due)

    short = _first_contribution(first_paycheck, frequency, 2, bill)
    long = _first_contribution(first_paycheck, frequency, 40, bill)

    assert short == long == expected


def test_schedule_range_does_not_change_the_reserve(client: TestClient, db) -> None:
    _make_schedule(db)
    resp = client.post(
        "/bills",
        json={
            "name": "Insurance",
            "amount": "1200.00",
            "recurrence": "annual",
            "due_date": "2025-12-01",
            "category": "insurance",
            "sinking_fund_enabled": True,
        },
    )
    assert resp.status_code == 201

    def first_contribution(to: str) -> str:
        periods = client.get(f"/schedule?from=2025-01-03&to={to}").json()["periods"]
        return periods[0]["sinking_fund_contributions"][0]["contribution_amount"]

    assert first_contribution("2025-01-16") == "52.17"
    assert first_contribution("2025-11-01") == "52.17"


def test_mismatched_pay_calendar_fails_loudly() -> None:
    periods = build_periods(date(2025, 1, 3), PayFrequency.biweekly, 4)

    with pytest.raises(ValueError, match="pay calendar"):
        apply_sinking_funds(
            periods,
            [_annual_sinking("1200", date(2025, 12, 1))],
            first_paycheck_date=date(2025, 1, 10),
            frequency=PayFrequency.biweekly,
        )
