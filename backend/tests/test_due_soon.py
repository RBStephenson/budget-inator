"""Unit tests for the due-soon digest selection and rendering (BI-75)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.schemas.schedule import AssignedBillOut, PayPeriodOut
from app.services.due_soon import (
    MAX_WINDOW_DAYS,
    render_error,
    render_markdown,
    select_due_soon,
)

TODAY = date(2026, 11, 14)


def _bill(
    bill_id: int,
    name: str,
    due: date,
    status: str = "on_time",
    amount: str = "100.00",
    **extra: object,
) -> AssignedBillOut:
    return AssignedBillOut(
        bill_id=bill_id,
        name=name,
        due_date=due,
        amount=Decimal(amount),
        status=status,
        **extra,
    )


def _period(
    start: date,
    end: date,
    bills: list[AssignedBillOut],
    pay_date: date | None = None,
    index: int = 0,
) -> PayPeriodOut:
    return PayPeriodOut(
        period_index=index,
        pay_date=pay_date or start,
        original_pay_date=start,
        period_start=start,
        period_end=end,
        opening_balance=Decimal("0"),
        total_bills=Decimal("0"),
        remaining_balance=Decimal("0"),
        period_result=Decimal("0"),
        flagged_bill_count=0,
        assigned_bills=bills,
    )


# Current period started yesterday, so today is not a payday.
NOT_PAYDAY_START = date(2026, 11, 13)
PERIOD_END = date(2026, 11, 26)


def _names(digest) -> list[str]:
    return [item.name for item in digest.items]


class TestWindow:
    def test_includes_today_and_last_day_excludes_day_after_and_yesterday(self) -> None:
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [
                    _bill(1, "Yesterday", date(2026, 11, 13)),
                    _bill(2, "Today", date(2026, 11, 14)),
                    _bill(3, "Last day", date(2026, 11, 17)),
                    _bill(4, "Day after", date(2026, 11, 18)),
                ],
            )
        ]

        digest = select_due_soon(periods, TODAY, window_days=3)

        assert _names(digest) == ["Today", "Last day"]
        assert digest.window_end == date(2026, 11, 17)
        assert digest.is_payday is False

    def test_zero_days_means_today_only(self) -> None:
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [_bill(1, "Today", TODAY), _bill(2, "Tomorrow", date(2026, 11, 15))],
            )
        ]

        assert _names(select_due_soon(periods, TODAY, window_days=0)) == ["Today"]

    def test_spans_into_the_next_period(self) -> None:
        periods = [
            _period(date(2026, 11, 1), TODAY, [_bill(1, "Today", TODAY)], index=0),
            _period(
                date(2026, 11, 15),
                date(2026, 11, 28),
                [_bill(2, "Next period", date(2026, 11, 16))],
                index=1,
            ),
        ]

        assert _names(select_due_soon(periods, TODAY, window_days=3)) == [
            "Today",
            "Next period",
        ]

    @pytest.mark.parametrize("days", [-1, MAX_WINDOW_DAYS + 1])
    def test_rejects_out_of_range_window(self, days: int) -> None:
        with pytest.raises(ValueError):
            select_due_soon([], TODAY, window_days=days)

    def test_empty_schedule_gives_empty_digest(self) -> None:
        digest = select_due_soon([], TODAY)

        assert digest.items == ()
        assert digest.total == Decimal("0")


class TestPayday:
    def test_payday_lists_the_whole_pay_period(self) -> None:
        periods = [
            _period(
                TODAY,
                date(2026, 11, 27),
                [
                    _bill(1, "Soon", date(2026, 11, 15)),
                    _bill(2, "Late in period", date(2026, 11, 26)),
                ],
            )
        ]

        digest = select_due_soon(periods, TODAY, window_days=3)

        assert digest.is_payday is True
        assert digest.window_end == date(2026, 11, 27)
        assert _names(digest) == ["Soon", "Late in period"]

    def test_overridden_pay_date_counts_as_the_payday(self) -> None:
        periods = [
            _period(
                date(2026, 11, 13),
                PERIOD_END,
                [_bill(1, "Late in period", date(2026, 11, 25))],
                pay_date=TODAY,
            )
        ]

        digest = select_due_soon(periods, TODAY, window_days=3)

        assert digest.is_payday is True
        assert _names(digest) == ["Late in period"]

    def test_pay_date_moved_earlier_than_its_period_start_is_still_payday(
        self,
    ) -> None:
        # Holiday case: the engine keeps period_start at the original date, so
        # today falls inside the *previous* period's range.
        periods = [
            _period(date(2026, 10, 31), date(2026, 11, 14), [], index=0),
            _period(
                date(2026, 11, 15),
                date(2026, 11, 28),
                [_bill(1, "Late in period", date(2026, 11, 27))],
                pay_date=TODAY,
                index=1,
            ),
        ]

        digest = select_due_soon(periods, TODAY, window_days=3)

        assert digest.is_payday is True
        assert digest.window_end == date(2026, 11, 28)
        assert _names(digest) == ["Late in period"]

    def test_day_after_payday_is_back_to_the_short_window(self) -> None:
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [_bill(1, "Late in period", date(2026, 11, 25))],
            )
        ]

        digest = select_due_soon(periods, TODAY, window_days=3)

        assert digest.is_payday is False
        assert digest.items == ()


class TestWhichBills:
    def test_skipped_bills_are_left_out(self) -> None:
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [_bill(1, "Skipped", TODAY, status="skipped"), _bill(2, "Kept", TODAY)],
            )
        ]

        assert _names(select_due_soon(periods, TODAY)) == ["Kept"]

    def test_carried_copy_in_the_window_is_listed(self) -> None:
        # A bill moved to an earlier paycheck and never marked can survive
        # only as a carried copy; dropping it would hide a bill due tomorrow.
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [_bill(1, "Moved early", date(2026, 11, 15), is_carried_over=True)],
            )
        ]

        assert _names(select_due_soon(periods, TODAY)) == ["Moved early"]

    def test_past_due_carried_copy_is_not_listed(self) -> None:
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [_bill(1, "Past due", date(2026, 11, 7), is_carried_over=True)],
            )
        ]

        assert select_due_soon(periods, TODAY).items == ()

    def test_paid_bills_stay_listed_and_are_tagged(self) -> None:
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [_bill(1, "Paid", TODAY, status="paid"), _bill(2, "Unpaid", TODAY)],
            )
        ]

        digest = select_due_soon(periods, TODAY)

        assert [(i.name, i.marked_paid) for i in digest.items] == [
            ("Paid", True),
            ("Unpaid", False),
        ]

    def test_a_bill_in_two_periods_is_listed_once(self) -> None:
        same = _bill(1, "Twice", date(2026, 11, 15))
        periods = [
            _period(NOT_PAYDAY_START, PERIOD_END, [same], index=0),
            _period(NOT_PAYDAY_START, PERIOD_END, [same], index=1),
        ]

        assert _names(select_due_soon(periods, TODAY)) == ["Twice"]

    def test_actual_amount_wins_over_the_estimate(self) -> None:
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [
                    _bill(
                        1,
                        "Power",
                        TODAY,
                        amount="100.00",
                        actual_amount=Decimal("87.50"),
                    )
                ],
            )
        ]

        digest = select_due_soon(periods, TODAY)

        assert digest.items[0].amount == Decimal("87.50")
        assert digest.total == Decimal("87.50")

    def test_sorted_by_date_then_name(self) -> None:
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [
                    _bill(1, "beta", date(2026, 11, 15)),
                    _bill(2, "Zeta", TODAY),
                    _bill(3, "Alpha", date(2026, 11, 15)),
                ],
            )
        ]

        assert _names(select_due_soon(periods, TODAY)) == ["Zeta", "Alpha", "beta"]


class TestRender:
    def test_first_line_dates_the_file(self) -> None:
        text = render_markdown(select_due_soon([], TODAY))

        assert text.splitlines()[0] == "generated: 2026-11-14"
        assert text.splitlines()[1] == "status: ok"

    def test_lists_bills_with_tags_and_total(self) -> None:
        periods = [
            _period(
                NOT_PAYDAY_START,
                PERIOD_END,
                [
                    _bill(1, "Phone", TODAY, amount="85.00", status="paid"),
                    _bill(
                        2,
                        "Power",
                        date(2026, 11, 15),
                        amount="1234.50",
                        is_variable=True,
                    ),
                ],
            )
        ]

        text = render_markdown(select_due_soon(periods, TODAY))

        assert "- Sat Nov 14: Phone, $85.00 (marked paid)" in text
        assert "- Sun Nov 15: Power, ~$1,234.50" in text
        assert "Total: $1,319.50 across 2 bills." in text
        assert "Next 3 days" in text

    def test_empty_window_says_so(self) -> None:
        text = render_markdown(select_due_soon([], TODAY))

        assert "No bills due in this window." in text
        assert "Total:" not in text

    def test_payday_heading(self) -> None:
        periods = [_period(TODAY, date(2026, 11, 27), [])]

        text = render_markdown(select_due_soon(periods, TODAY))

        assert "Payday: the whole pay period" in text

    def test_error_file_is_dated_and_marked(self) -> None:
        text = render_error(TODAY, "FileNotFoundError: nope")

        assert text.splitlines()[:2] == ["generated: 2026-11-14", "status: error"]
        assert "FAILED" in text
        assert "FileNotFoundError: nope" in text
