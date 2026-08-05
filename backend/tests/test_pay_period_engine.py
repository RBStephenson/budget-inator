"""Unit tests for the pay-period assignment engine.

No DB, no HTTP — pure logic only.
"""

import time
from datetime import date, timedelta
from decimal import Decimal

from app.models.enums import BillRecurrence, PayFrequency
from app.services.pay_period_engine import (
    ActualAnchor,
    BillInput,
    PayPeriodResult,
    assign_bills,
    build_periods,
    due_dates_for_bill,
    project,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SALARY = Decimal("2500.00")
ZERO = Decimal("0.00")


def _bill(
    *,
    id: int = 1,
    name: str = "Rent",
    amount: str = "1200.00",
    recurrence: BillRecurrence = BillRecurrence.monthly,
    due_day: int | None = 1,
    first_due_date: date | None = None,
    grace: int = 0,
) -> BillInput:
    return BillInput(
        id=id,
        name=name,
        amount=Decimal(amount),
        recurrence=recurrence,
        due_day=due_day,
        first_due_date=first_due_date,
        grace_period_days=grace,
    )


def _biweekly_periods(n: int = 3) -> list[PayPeriodResult]:
    """Build biweekly periods without balances applied (use project() for balances)."""
    return build_periods(date(2024, 1, 5), PayFrequency.biweekly, n)


# ---------------------------------------------------------------------------
# build_periods — period boundaries
# ---------------------------------------------------------------------------


class TestBuildPeriods:
    def test_biweekly_boundaries(self) -> None:
        periods = _biweekly_periods(3)
        assert len(periods) == 3
        assert periods[0].period_start == date(2024, 1, 5)
        assert periods[0].period_end == date(2024, 1, 18)
        assert periods[1].period_start == date(2024, 1, 19)
        assert periods[1].period_end == date(2024, 2, 1)
        assert periods[2].period_start == date(2024, 2, 2)
        assert periods[2].period_end == date(2024, 2, 15)

    def test_weekly_boundaries(self) -> None:
        periods = build_periods(date(2024, 1, 5), PayFrequency.weekly, 2)
        assert periods[0].period_end == date(2024, 1, 11)
        assert periods[1].period_start == date(2024, 1, 12)

    def test_semimonthly_boundaries(self) -> None:
        periods = build_periods(date(2024, 1, 1), PayFrequency.semimonthly, 4)
        assert periods[0].period_start == date(2024, 1, 1)
        assert periods[0].period_end == date(2024, 1, 14)
        assert periods[1].period_start == date(2024, 1, 15)
        assert periods[1].period_end == date(2024, 1, 31)
        assert periods[2].period_start == date(2024, 2, 1)
        assert periods[3].period_start == date(2024, 2, 15)

    def test_semimonthly_month_end_pattern_across_leap_february(self) -> None:
        periods = build_periods(date(2024, 1, 31), PayFrequency.semimonthly, 5)
        assert [period.pay_date for period in periods] == [
            date(2024, 1, 31),
            date(2024, 2, 15),
            date(2024, 2, 29),
            date(2024, 3, 15),
            date(2024, 3, 31),
        ]

    def test_semimonthly_month_end_pattern_across_non_leap_february(self) -> None:
        periods = build_periods(date(2025, 1, 31), PayFrequency.semimonthly, 3)
        assert [period.pay_date for period in periods] == [
            date(2025, 1, 31),
            date(2025, 2, 15),
            date(2025, 2, 28),
        ]

    def test_semimonthly_adjusted_month_end_anchor_keeps_pattern(self) -> None:
        periods = build_periods(date(2026, 5, 29), PayFrequency.semimonthly, 4)
        assert [period.pay_date for period in periods] == [
            date(2026, 5, 29),
            date(2026, 6, 15),
            date(2026, 6, 30),
            date(2026, 7, 15),
        ]

    def test_semimonthly_fifteenth_anchor_keeps_first_and_fifteenth_pattern(
        self,
    ) -> None:
        periods = build_periods(date(2024, 1, 15), PayFrequency.semimonthly, 3)
        assert [period.pay_date for period in periods] == [
            date(2024, 1, 15),
            date(2024, 2, 1),
            date(2024, 2, 15),
        ]

    def test_monthly_boundaries(self) -> None:
        periods = build_periods(date(2024, 1, 15), PayFrequency.monthly, 3)
        assert periods[0].period_start == date(2024, 1, 15)
        assert periods[0].period_end == date(2024, 2, 14)
        assert periods[1].period_start == date(2024, 2, 15)

    def test_monthly_day_31_anchor_does_not_drift_after_short_month(self) -> None:
        # Feb clamps to the 29th (2024 is a leap year); March has 31 days again
        # and should recover the original day instead of staying clamped.
        periods = build_periods(date(2024, 1, 31), PayFrequency.monthly, 3)
        assert [period.pay_date for period in periods] == [
            date(2024, 1, 31),
            date(2024, 2, 29),
            date(2024, 3, 31),
        ]

    def test_pay_date_equals_period_start(self) -> None:
        periods = _biweekly_periods(2)
        for p in periods:
            assert p.pay_date == p.period_start

    def test_period_index(self) -> None:
        periods = _biweekly_periods(3)
        assert [p.period_index for p in periods] == [0, 1, 2]

    def test_no_gaps_between_periods(self) -> None:
        periods = _biweekly_periods(4)
        for a, b in zip(periods, periods[1:]):
            assert b.period_start == a.period_end + timedelta(days=1)


# ---------------------------------------------------------------------------
# build_periods — rolling balances
# ---------------------------------------------------------------------------


class TestRollingBalance:
    def test_first_period_opening_adds_beginning_balance(self) -> None:
        periods = project(
            date(2024, 1, 5), PayFrequency.biweekly, 1, SALARY, Decimal("500.00"), []
        )
        assert periods[0].opening_balance == Decimal("3000.00")

    def test_zero_beginning_balance(self) -> None:
        periods = project(date(2024, 1, 5), PayFrequency.biweekly, 1, SALARY, ZERO, [])
        assert periods[0].opening_balance == SALARY

    def test_remaining_balance_no_bills(self) -> None:
        periods = project(date(2024, 1, 5), PayFrequency.biweekly, 1, SALARY, ZERO, [])
        assert periods[0].remaining_balance == SALARY

    def test_rolling_balance_carries_over(self) -> None:
        # Period 0: opens 2500, one bill 1000 → remaining 1500
        # Period 1: opens 1500 + 2500 = 4000
        bill = _bill(amount="1000.00", due_day=10)  # due Jan 10, in period 0
        periods = project(
            date(2024, 1, 5), PayFrequency.biweekly, 2, SALARY, ZERO, [bill]
        )
        assert periods[0].remaining_balance == Decimal("1500.00")
        assert periods[1].opening_balance == Decimal("4000.00")

    def test_negative_carry_over(self) -> None:
        # Overspend in period 0 → negative carry
        bill = _bill(amount="3000.00", due_day=10)
        periods = project(
            date(2024, 1, 5), PayFrequency.biweekly, 2, SALARY, ZERO, [bill]
        )
        assert periods[0].remaining_balance == Decimal("-500.00")
        assert periods[1].opening_balance == Decimal("2000.00")


class TestActualsReanchor:
    """#55: confirmed payday actuals override the computed projection."""

    # biweekly from 2024-01-05 → pay dates 01-05, 01-19, 02-02

    def test_actual_balance_reanchors_opening(self) -> None:
        actuals = {date(2024, 1, 5): ActualAnchor(actual_balance=Decimal("1000.00"))}
        periods = project(
            date(2024, 1, 5),
            PayFrequency.biweekly,
            2,
            SALARY,
            Decimal("500.00"),
            [],
            actuals,
        )
        # Opening is the actual balance, not beginning_balance + salary.
        assert periods[0].opening_balance == Decimal("1000.00")
        # Next period rolls forward from there (deposit already reflected).
        assert periods[1].opening_balance == Decimal("3500.00")

    def test_actual_balance_on_later_period_only_affects_from_there(self) -> None:
        actuals = {date(2024, 1, 19): ActualAnchor(actual_balance=Decimal("999.00"))}
        periods = project(
            date(2024, 1, 5), PayFrequency.biweekly, 3, SALARY, ZERO, [], actuals
        )
        assert periods[0].opening_balance == SALARY  # unchanged
        assert periods[1].opening_balance == Decimal("999.00")  # re-anchored
        assert periods[2].opening_balance == Decimal("3499.00")  # 999 + salary

    def test_actual_net_pay_overrides_salary_for_that_period_only(self) -> None:
        actuals = {date(2024, 1, 5): ActualAnchor(actual_net_pay=Decimal("100.00"))}
        periods = project(
            date(2024, 1, 5), PayFrequency.biweekly, 2, SALARY, ZERO, [], actuals
        )
        # Period 0 uses the actual net pay...
        assert periods[0].opening_balance == Decimal("100.00")
        # ...but period 1 reverts to the assumed salary (100 + 2500).
        assert periods[1].opening_balance == Decimal("2600.00")

    def test_actual_balance_takes_precedence_over_net_pay(self) -> None:
        actuals = {
            date(2024, 1, 5): ActualAnchor(
                actual_net_pay=Decimal("100.00"),
                actual_balance=Decimal("777.00"),
            )
        }
        periods = project(
            date(2024, 1, 5), PayFrequency.biweekly, 1, SALARY, ZERO, [], actuals
        )
        assert periods[0].opening_balance == Decimal("777.00")

    def test_empty_actuals_leaves_projection_unchanged(self) -> None:
        periods = project(
            date(2024, 1, 5),
            PayFrequency.biweekly,
            1,
            SALARY,
            Decimal("500.00"),
            [],
            {},
        )
        assert periods[0].opening_balance == Decimal("3000.00")


# ---------------------------------------------------------------------------
# due_dates_for_bill
# ---------------------------------------------------------------------------


class TestDueDatesForBill:
    def test_monthly_single_occurrence(self) -> None:
        bill = _bill(recurrence=BillRecurrence.monthly, due_day=15)
        dates = due_dates_for_bill(bill, date(2024, 1, 1), date(2024, 1, 31))
        assert dates == [date(2024, 1, 15)]

    def test_monthly_multiple_months(self) -> None:
        bill = _bill(recurrence=BillRecurrence.monthly, due_day=1)
        dates = due_dates_for_bill(bill, date(2024, 1, 1), date(2024, 3, 31))
        assert dates == [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)]

    def test_monthly_due_day_clamped_for_short_month(self) -> None:
        # due_day=31; February should clamp to Feb 28 (2024 is a leap year → 29)
        bill = _bill(recurrence=BillRecurrence.monthly, due_day=28)
        dates = due_dates_for_bill(bill, date(2024, 2, 1), date(2024, 2, 29))
        assert dates == [date(2024, 2, 28)]

    def test_monthly_window_starts_after_due_day(self) -> None:
        # Window Jan 20 – Feb 28; due_day=15; first hit is Feb 15
        bill = _bill(recurrence=BillRecurrence.monthly, due_day=15)
        dates = due_dates_for_bill(bill, date(2024, 1, 20), date(2024, 2, 28))
        assert dates == [date(2024, 2, 15)]

    def test_biweekly_multiple_occurrences(self) -> None:
        bill = _bill(
            recurrence=BillRecurrence.biweekly,
            due_day=None,
            first_due_date=date(2024, 1, 5),
        )
        dates = due_dates_for_bill(bill, date(2024, 1, 1), date(2024, 2, 15))
        assert dates == [date(2024, 1, 5), date(2024, 1, 19), date(2024, 2, 2)]

    def test_biweekly_anchor_before_window(self) -> None:
        bill = _bill(
            recurrence=BillRecurrence.biweekly,
            due_day=None,
            first_due_date=date(2023, 12, 1),
        )
        dates = due_dates_for_bill(bill, date(2024, 1, 1), date(2024, 1, 31))
        # Sequence from Dec 1: Dec 1, 15, 29, Jan 12, 26
        assert date(2024, 1, 12) in dates
        assert date(2024, 1, 26) in dates
        assert all(date(2024, 1, 1) <= d <= date(2024, 1, 31) for d in dates)

    def test_biweekly_anchor_after_window_start(self) -> None:
        bill = _bill(
            recurrence=BillRecurrence.biweekly,
            due_day=None,
            first_due_date=date(2024, 1, 19),
        )
        dates = due_dates_for_bill(bill, date(2024, 1, 5), date(2024, 2, 15))
        assert dates == [date(2024, 1, 19), date(2024, 2, 2)]

    def test_weekly_four_occurrences(self) -> None:
        bill = _bill(
            recurrence=BillRecurrence.weekly,
            due_day=None,
            first_due_date=date(2024, 1, 5),
        )
        dates = due_dates_for_bill(bill, date(2024, 1, 5), date(2024, 1, 28))
        assert dates == [
            date(2024, 1, 5),
            date(2024, 1, 12),
            date(2024, 1, 19),
            date(2024, 1, 26),
        ]

    def test_quarterly(self) -> None:
        bill = _bill(
            recurrence=BillRecurrence.quarterly,
            due_day=None,
            first_due_date=date(2024, 1, 15),
        )
        dates = due_dates_for_bill(bill, date(2024, 1, 1), date(2024, 12, 31))
        assert dates == [
            date(2024, 1, 15),
            date(2024, 4, 15),
            date(2024, 7, 15),
            date(2024, 10, 15),
        ]

    def test_quarterly_day_31_anchor_does_not_drift_after_short_month(self) -> None:
        # Jan 31 -> Apr 30 (clamped, April has 30 days) -> should recover to
        # Jul 31 rather than staying clamped at the 30th.
        bill = _bill(
            recurrence=BillRecurrence.quarterly,
            due_day=None,
            first_due_date=date(2024, 1, 31),
        )
        dates = due_dates_for_bill(bill, date(2024, 1, 1), date(2024, 12, 31))
        assert dates == [
            date(2024, 1, 31),
            date(2024, 4, 30),
            date(2024, 7, 31),
            date(2024, 10, 31),
        ]

    def test_annual(self) -> None:
        bill = _bill(
            recurrence=BillRecurrence.annual,
            due_day=None,
            first_due_date=date(2024, 3, 1),
        )
        dates = due_dates_for_bill(bill, date(2024, 1, 1), date(2025, 12, 31))
        assert dates == [date(2024, 3, 1), date(2025, 3, 1)]

    def test_one_time_in_window(self) -> None:
        bill = _bill(
            recurrence=BillRecurrence.one_time,
            due_day=None,
            first_due_date=date(2024, 1, 20),
        )
        dates = due_dates_for_bill(bill, date(2024, 1, 1), date(2024, 1, 31))
        assert dates == [date(2024, 1, 20)]

    def test_one_time_outside_window(self) -> None:
        bill = _bill(
            recurrence=BillRecurrence.one_time,
            due_day=None,
            first_due_date=date(2024, 3, 1),
        )
        dates = due_dates_for_bill(bill, date(2024, 1, 1), date(2024, 1, 31))
        assert dates == []

    def test_no_dates_when_window_precedes_first_occurrence(self) -> None:
        bill = _bill(recurrence=BillRecurrence.monthly, due_day=28)
        dates = due_dates_for_bill(bill, date(2024, 1, 29), date(2024, 1, 31))
        assert dates == []


# ---------------------------------------------------------------------------
# assign_bills — normal assignment
# ---------------------------------------------------------------------------


class TestAssignBills:
    def test_bill_assigned_to_containing_period(self) -> None:
        periods = _biweekly_periods(3)
        # Period 0: Jan 5–18; bill due Jan 10
        bill = _bill(due_day=10)
        assign_bills(periods, [bill])
        assert len(periods[0].assigned_bills) == 1
        assert periods[0].assigned_bills[0].due_date == date(2024, 1, 10)
        assert periods[0].assigned_bills[0].status == "on_time"

    def test_bill_due_on_period_start_boundary(self) -> None:
        periods = _biweekly_periods(3)
        # Period 1 starts Jan 19; bill due Jan 19
        bill = _bill(due_day=19)
        assign_bills(periods, [bill])
        assert len(periods[1].assigned_bills) == 1
        assert periods[1].assigned_bills[0].status == "on_time"

    def test_bill_due_on_period_end_boundary(self) -> None:
        periods = _biweekly_periods(3)
        # Period 0 ends Jan 18; bill due Jan 18
        bill = _bill(due_day=18)
        assign_bills(periods, [bill])
        assert len(periods[0].assigned_bills) == 1
        assert periods[0].assigned_bills[0].status == "on_time"

    def test_multiple_bills_sorted_by_due_date(self) -> None:
        periods = _biweekly_periods(3)
        b1 = _bill(id=1, name="Rent", due_day=15)
        b2 = _bill(id=2, name="Electric", due_day=8)
        assign_bills(periods, [b1, b2])
        due_dates = [b.due_date for b in periods[0].assigned_bills]
        assert due_dates == sorted(due_dates)

    def test_bills_span_multiple_periods(self) -> None:
        periods = _biweekly_periods(3)
        b1 = _bill(id=1, name="Rent", due_day=10)  # period 0
        b2 = _bill(id=2, name="Car", due_day=25)  # period 1 (Jan 19–Feb 1)
        assign_bills(periods, [b1, b2])
        assert any(b.name == "Rent" for b in periods[0].assigned_bills)
        assert any(b.name == "Car" for b in periods[1].assigned_bills)

    def test_empty_bills_list(self) -> None:
        periods = _biweekly_periods(3)
        assign_bills(periods, [])
        assert all(len(p.assigned_bills) == 0 for p in periods)

    def test_empty_periods_list(self) -> None:
        result = assign_bills([], [_bill()])
        assert result == []

    def test_remaining_balance_updated(self) -> None:
        bill = _bill(amount="500.00", due_day=10)
        periods = project(
            date(2024, 1, 5), PayFrequency.biweekly, 2, SALARY, ZERO, [bill]
        )
        assert periods[0].remaining_balance == Decimal("2000.00")


# ---------------------------------------------------------------------------
# assign_bills — late flagging
# ---------------------------------------------------------------------------


class TestLateFlagging:
    def test_bill_due_before_first_period_is_late_flagged(self) -> None:
        # First paycheck Jan 5; bill due Jan 3
        periods = build_periods(date(2024, 1, 5), PayFrequency.biweekly, 3)
        bill = BillInput(
            id=1,
            name="Overdue",
            amount=Decimal("100.00"),
            recurrence=BillRecurrence.one_time,
            due_day=None,
            first_due_date=date(2024, 1, 3),
        )
        assign_bills(periods, [bill])
        assert len(periods[0].assigned_bills) == 1
        assert periods[0].assigned_bills[0].status == "late_flagged"

    def test_late_flagged_bill_lands_in_first_period(self) -> None:
        periods = build_periods(date(2024, 2, 1), PayFrequency.biweekly, 2)
        bill = BillInput(
            id=1,
            name="Old Bill",
            amount=Decimal("50.00"),
            recurrence=BillRecurrence.one_time,
            due_day=None,
            first_due_date=date(2024, 1, 15),
        )
        assign_bills(periods, [bill])
        assert periods[0].assigned_bills[0].status == "late_flagged"
        assert len(periods[1].assigned_bills) == 0


# ---------------------------------------------------------------------------
# assign_bills — grace period
# ---------------------------------------------------------------------------


class TestGracePeriod:
    def test_grace_defaults_to_due_date_period_when_funds_allow(self) -> None:
        # Period 0: Jan 5–18; Period 1: Jan 19–Feb 1
        # Bill due Jan 17, grace 5 days, but nothing else competing for
        # funds → stays in its due-date period rather than shifting to the
        # end of the grace window (Jan 22, period 1).
        periods = _biweekly_periods(3)
        bill = BillInput(
            id=1,
            name="Flexible",
            amount=Decimal("200.00"),
            recurrence=BillRecurrence.one_time,
            due_day=None,
            first_due_date=date(2024, 1, 17),
            grace_period_days=5,
        )
        assign_bills(periods, [bill])
        assert len(periods[0].assigned_bills) == 1
        assert periods[0].assigned_bills[0].due_date == date(2024, 1, 17)
        assert len(periods[1].assigned_bills) == 0

    def test_zero_grace_uses_actual_due_date(self) -> None:
        periods = _biweekly_periods(3)
        bill = BillInput(
            id=1,
            name="NoGrace",
            amount=Decimal("100.00"),
            recurrence=BillRecurrence.one_time,
            due_day=None,
            first_due_date=date(2024, 1, 17),
            grace_period_days=0,
        )
        assign_bills(periods, [bill])
        assert len(periods[0].assigned_bills) == 1

    def test_grace_rescues_late_flagged_bill(self) -> None:
        # First period starts Jan 5; bill due Jan 3, grace 3 → effective Jan 6
        periods = build_periods(date(2024, 1, 5), PayFrequency.biweekly, 2)
        bill = BillInput(
            id=1,
            name="AlmostLate",
            amount=Decimal("75.00"),
            recurrence=BillRecurrence.one_time,
            due_day=None,
            first_due_date=date(2024, 1, 3),
            grace_period_days=3,
        )
        assign_bills(periods, [bill])
        assert periods[0].assigned_bills[0].status == "on_time"

    def test_project_keeps_grace_bill_at_due_date_when_funds_allow(
        self,
    ) -> None:
        # PENNYMAC's due-date period (period 0) covers both bills fine, so
        # it should stay there by default rather than drifting to the end
        # of its grace window.
        bills = [
            BillInput(
                id=1,
                name="PENNYMAC",
                amount=Decimal("900.00"),
                recurrence=BillRecurrence.one_time,
                due_day=None,
                first_due_date=date(2024, 1, 17),
                grace_period_days=5,
            ),
            BillInput(
                id=2,
                name="Car",
                amount=Decimal("900.00"),
                recurrence=BillRecurrence.one_time,
                due_day=None,
                first_due_date=date(2024, 1, 25),
            ),
        ]

        periods = project(
            date(2024, 1, 5),
            PayFrequency.biweekly,
            2,
            Decimal("2000.00"),
            ZERO,
            bills,
            actuals={
                date(2024, 1, 19): ActualAnchor(actual_balance=Decimal("1000.00"))
            },
        )

        assert [bill.name for bill in periods[0].assigned_bills] == ["PENNYMAC"]
        assert [bill.name for bill in periods[1].assigned_bills] == ["Car"]
        assert periods[0].remaining_balance == Decimal("1100.00")
        assert periods[1].remaining_balance == Decimal("100.00")

    def test_project_moves_grace_bill_forward_to_avoid_overbooked_period(
        self,
    ) -> None:
        # PENNYMAC defaults to period 0 (its due date), but period 0 can't
        # cover both bills on a $1000 salary — only the grace bill has
        # anywhere else to go, so it rolls forward into period 1.
        bills = [
            BillInput(
                id=1,
                name="PENNYMAC",
                amount=Decimal("900.00"),
                recurrence=BillRecurrence.one_time,
                due_day=None,
                first_due_date=date(2024, 1, 17),
                grace_period_days=5,
            ),
            BillInput(
                id=2,
                name="Utilities",
                amount=Decimal("900.00"),
                recurrence=BillRecurrence.one_time,
                due_day=None,
                first_due_date=date(2024, 1, 12),
            ),
        ]

        periods = project(
            date(2024, 1, 5),
            PayFrequency.biweekly,
            2,
            Decimal("1000.00"),
            ZERO,
            bills,
        )

        assert [bill.name for bill in periods[0].assigned_bills] == ["Utilities"]
        assert [bill.name for bill in periods[1].assigned_bills] == ["PENNYMAC"]
        assert periods[0].remaining_balance == Decimal("100.00")
        assert periods[1].remaining_balance == Decimal("200.00")

    def test_rebalance_uses_grace_of_version_active_at_due_date(self) -> None:
        # Same scenario as
        # test_project_moves_grace_bill_backward_to_avoid_overbooked_period, but
        # PENNYMAC's terms are split across two versions sharing id=1: the
        # active one (grace=5) generates the Jan 17 due date, while a decoy
        # future version (grace=0, active from Jan 21 on) generates no
        # occurrence in this window at all. Rebalancing must use the grace of
        # the version that actually produced the occurrence, not whichever
        # version happens to be last in the list.
        bills = [
            BillInput(
                id=1,
                name="PENNYMAC",
                amount=Decimal("900.00"),
                recurrence=BillRecurrence.one_time,
                due_day=None,
                first_due_date=date(2024, 1, 17),
                grace_period_days=5,
                active_start=date(2024, 1, 1),
                active_end=date(2024, 1, 20),
            ),
            BillInput(
                id=1,
                name="PENNYMAC",
                amount=Decimal("900.00"),
                recurrence=BillRecurrence.one_time,
                due_day=None,
                first_due_date=date(2024, 1, 17),
                grace_period_days=0,
                active_start=date(2024, 1, 21),
                active_end=date(2024, 2, 1),
            ),
            BillInput(
                id=2,
                name="Car",
                amount=Decimal("900.00"),
                recurrence=BillRecurrence.one_time,
                due_day=None,
                first_due_date=date(2024, 1, 25),
            ),
        ]

        periods = project(
            date(2024, 1, 5),
            PayFrequency.biweekly,
            2,
            Decimal("2000.00"),
            ZERO,
            bills,
            actuals={
                date(2024, 1, 19): ActualAnchor(actual_balance=Decimal("1000.00"))
            },
        )

        assert [bill.name for bill in periods[0].assigned_bills] == ["PENNYMAC"]
        assert [bill.name for bill in periods[1].assigned_bills] == ["Car"]
        assert periods[0].remaining_balance == Decimal("1100.00")
        assert periods[1].remaining_balance == Decimal("100.00")


# ---------------------------------------------------------------------------
# assign_bills — paid-bill relocation
# ---------------------------------------------------------------------------


class TestPaidBillRelocation:
    """A paid occurrence is assigned to the period containing its paid date."""

    def test_future_bill_paid_early_moves_to_current_period(self) -> None:
        # Period 0: Jan 5–18; Period 1: Jan 19–Feb 1. Bill due Jan 25 (period 1)
        # but paid Jan 10 (period 0) → should land in period 0.
        periods = _biweekly_periods(3)
        bill = _bill(due_day=25)
        paid = {(bill.id, date(2024, 1, 25)): date(2024, 1, 10)}
        assign_bills(periods, [bill], paid)
        assert [b.due_date for b in periods[0].assigned_bills] == [date(2024, 1, 25)]
        assert periods[1].assigned_bills == []

    def test_past_bill_paid_late_moves_to_later_period(self) -> None:
        # Bill due Jan 10 (period 0) but paid Jan 22 (period 1).
        periods = _biweekly_periods(3)
        bill = _bill(due_day=10)
        paid = {(bill.id, date(2024, 1, 10)): date(2024, 1, 22)}
        assign_bills(periods, [bill], paid)
        assert periods[0].assigned_bills == []
        assert [b.due_date for b in periods[1].assigned_bills] == [date(2024, 1, 10)]

    def test_unpaid_bill_unaffected_by_relocation_map(self) -> None:
        periods = _biweekly_periods(3)
        bill = _bill(due_day=25)  # period 1
        # Map keyed by a different occurrence → no relocation.
        assign_bills(periods, [bill], {(99, date(2024, 1, 25)): date(2024, 1, 10)})
        assert [b.due_date for b in periods[1].assigned_bills] == [date(2024, 1, 25)]

    def test_paid_date_outside_periods_falls_back_to_due_date(self) -> None:
        # Paid date before all periods → fall back to normal due-date assignment.
        periods = _biweekly_periods(3)
        bill = _bill(due_day=25)  # period 1
        paid = {(bill.id, date(2024, 1, 25)): date(2023, 12, 1)}
        assign_bills(periods, [bill], paid)
        assert [b.due_date for b in periods[1].assigned_bills] == [date(2024, 1, 25)]

    def test_relocation_shifts_rolling_balances(self) -> None:
        # Bill due in period 1 but paid in period 0: the spend moves to period 0,
        # so period 0's remaining drops and period 1 opens higher.
        bill = _bill(amount="1000.00", due_day=25)  # period 1 normally
        paid = {(bill.id, date(2024, 1, 25)): date(2024, 1, 10)}
        periods = project(
            date(2024, 1, 5),
            PayFrequency.biweekly,
            2,
            SALARY,
            ZERO,
            [bill],
            paid_dates=paid,
        )
        assert periods[0].remaining_balance == Decimal("1500.00")  # 2500 - 1000
        assert periods[1].opening_balance == Decimal("4000.00")  # 1500 + 2500


# ---------------------------------------------------------------------------
# assign_bills — biweekly bill spanning multiple periods
# ---------------------------------------------------------------------------


class TestBiweeklyBillMultiplePeriods:
    def test_biweekly_bill_generates_instance_per_period(self) -> None:
        periods = _biweekly_periods(3)
        bill = BillInput(
            id=1,
            name="Loan",
            amount=Decimal("300.00"),
            recurrence=BillRecurrence.biweekly,
            due_day=None,
            first_due_date=date(2024, 1, 5),
        )
        assign_bills(periods, [bill])
        # Jan 5 → period 0, Jan 19 → period 1, Feb 2 → period 2
        assert any(b.due_date == date(2024, 1, 5) for b in periods[0].assigned_bills)
        assert any(b.due_date == date(2024, 1, 19) for b in periods[1].assigned_bills)
        assert any(b.due_date == date(2024, 2, 2) for b in periods[2].assigned_bills)

    def test_weekly_bill_four_instances_in_four_weeks(self) -> None:
        periods = build_periods(date(2024, 1, 5), PayFrequency.weekly, 4)
        bill = BillInput(
            id=1,
            name="Weekly Sub",
            amount=Decimal("10.00"),
            recurrence=BillRecurrence.weekly,
            due_day=None,
            first_due_date=date(2024, 1, 5),
        )
        assign_bills(periods, [bill])
        # One instance per period
        assert all(len(p.assigned_bills) == 1 for p in periods)


# ---------------------------------------------------------------------------
# project — integration
# ---------------------------------------------------------------------------


class TestProject:
    def test_full_projection(self) -> None:
        bills = [
            _bill(id=1, name="Rent", amount="1200.00", due_day=5),
            _bill(
                id=2,
                name="Car",
                amount="350.00",
                recurrence=BillRecurrence.biweekly,
                due_day=None,
                first_due_date=date(2024, 1, 12),
            ),
        ]
        periods = project(
            first_paycheck_date=date(2024, 1, 5),
            frequency=PayFrequency.biweekly,
            num_periods=3,
            net_salary=SALARY,
            beginning_balance=Decimal("500.00"),
            bills=bills,
        )
        assert len(periods) == 3
        # Period 0 (Jan 5–18): Rent Jan 5, Car Jan 12
        p0_names = {b.name for b in periods[0].assigned_bills}
        assert p0_names == {"Rent", "Car"}

    def test_returns_empty_list_for_zero_periods(self) -> None:
        result = project(
            first_paycheck_date=date(2024, 1, 5),
            frequency=PayFrequency.biweekly,
            num_periods=0,
            net_salary=SALARY,
            beginning_balance=ZERO,
            bills=[],
        )
        assert result == []


# ---------------------------------------------------------------------------
# project — actual amounts / skipped bills roll forward into later periods
# ---------------------------------------------------------------------------


class TestActualAmountAndSkipRollover:
    def test_skipped_bill_excluded_from_its_own_and_next_periods_balance(self) -> None:
        bill = _bill(due_day=5, amount="200.00")
        skipped_periods = project(
            first_paycheck_date=date(2024, 1, 5),
            frequency=PayFrequency.biweekly,
            num_periods=2,
            net_salary=SALARY,
            beginning_balance=ZERO,
            bills=[bill],
            skipped_dates={(bill.id, date(2024, 1, 5))},
        )
        baseline_periods = project(
            first_paycheck_date=date(2024, 1, 5),
            frequency=PayFrequency.biweekly,
            num_periods=2,
            net_salary=SALARY,
            beginning_balance=ZERO,
            bills=[bill],
        )
        # Skipping the bill frees its $200 for period 0 and, since that
        # balance rolls forward, for period 1's opening balance too.
        assert skipped_periods[0].remaining_balance == (
            baseline_periods[0].remaining_balance + Decimal("200.00")
        )
        assert skipped_periods[1].opening_balance == (
            baseline_periods[1].opening_balance + Decimal("200.00")
        )

    def test_actual_amount_overrides_estimate_for_rollover(self) -> None:
        bill = _bill(due_day=5, amount="200.00")
        periods = project(
            first_paycheck_date=date(2024, 1, 5),
            frequency=PayFrequency.biweekly,
            num_periods=2,
            net_salary=SALARY,
            beginning_balance=ZERO,
            bills=[bill],
            actual_amounts={(bill.id, date(2024, 1, 5)): Decimal("250.00")},
        )
        baseline_periods = project(
            first_paycheck_date=date(2024, 1, 5),
            frequency=PayFrequency.biweekly,
            num_periods=2,
            net_salary=SALARY,
            beginning_balance=ZERO,
            bills=[bill],
        )
        # Paying $50 over the $200 estimate costs $50 more in period 0, and
        # that shortfall rolls forward into period 1's opening balance too.
        assert periods[0].remaining_balance == (
            baseline_periods[0].remaining_balance - Decimal("50.00")
        )
        assert periods[1].opening_balance == (
            baseline_periods[1].opening_balance - Decimal("50.00")
        )


# ---------------------------------------------------------------------------
# rebalance_grace_period_bills — performance (BI-12)
# ---------------------------------------------------------------------------


class TestRebalancePerformance:
    def test_rebalance_completes_quickly_at_160_periods(self) -> None:
        """Reproduces BI-12's own benchmark scenario: 8 monthly grace-period
        bills, weekly pay, salary too low to cover them so every period
        stays in deficit and the rebalance pass keeps searching for moves.
        Before the O(range) rewrite of the candidate-scoring loop, this took
        ~110s at 160 periods; it should now complete in well under a second.
        """
        bills = [
            _bill(
                id=i,
                name=f"Bill{i}",
                amount="500.00",
                due_day=((i * 3) % 28) + 1,
                grace=10,
            )
            for i in range(1, 9)
        ]

        start = time.perf_counter()
        periods = project(
            first_paycheck_date=date(2024, 1, 1),
            frequency=PayFrequency.weekly,
            num_periods=160,
            net_salary=Decimal("300.00"),
            beginning_balance=ZERO,
            bills=bills,
        )
        elapsed = time.perf_counter() - start

        assert len(periods) == 160
        assert elapsed < 5.0, f"rebalance took {elapsed:.2f}s, expected well under 5s"
