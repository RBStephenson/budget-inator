from datetime import date
from decimal import Decimal

from app.models.enums import BillRecurrence
from app.services.pay_period_engine import BillInput, due_dates_for_bill


def _monthly_bill(
    *,
    due_day: int | None,
    due_day_is_month_end: bool = False,
) -> BillInput:
    return BillInput(
        id=1,
        name="Month-end bill",
        amount=Decimal("100.00"),
        recurrence=BillRecurrence.monthly,
        due_day=due_day,
        first_due_date=None,
        due_day_is_month_end=due_day_is_month_end,
    )


def test_fixed_31st_clamps_across_month_lengths_and_leap_february() -> None:
    dates = due_dates_for_bill(
        _monthly_bill(due_day=31),
        date(2024, 1, 1),
        date(2024, 4, 30),
    )
    assert dates == [
        date(2024, 1, 31),
        date(2024, 2, 29),
        date(2024, 3, 31),
        date(2024, 4, 30),
    ]


def test_fixed_30th_returns_to_30_after_non_leap_february() -> None:
    dates = due_dates_for_bill(
        _monthly_bill(due_day=30),
        date(2025, 1, 1),
        date(2025, 4, 30),
    )
    assert dates == [
        date(2025, 1, 30),
        date(2025, 2, 28),
        date(2025, 3, 30),
        date(2025, 4, 30),
    ]


def test_explicit_month_end_differs_from_fixed_30th_in_31_day_months() -> None:
    month_end_dates = due_dates_for_bill(
        _monthly_bill(due_day=None, due_day_is_month_end=True),
        date(2025, 3, 1),
        date(2025, 4, 30),
    )
    fixed_dates = due_dates_for_bill(
        _monthly_bill(due_day=30),
        date(2025, 3, 1),
        date(2025, 4, 30),
    )
    assert month_end_dates == [date(2025, 3, 31), date(2025, 4, 30)]
    assert fixed_dates == [date(2025, 3, 30), date(2025, 4, 30)]
