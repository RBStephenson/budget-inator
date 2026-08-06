from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import PayFrequency

FIRST_PAYCHECK_MAX_DAYS_PAST = 3653  # ~10 years
FIRST_PAYCHECK_MAX_DAYS_FUTURE = 183  # ~6 months


def _validate_first_paycheck_date(v: date) -> date:
    today = date.today()
    earliest = today - timedelta(days=FIRST_PAYCHECK_MAX_DAYS_PAST)
    latest = today + timedelta(days=FIRST_PAYCHECK_MAX_DAYS_FUTURE)
    if v < earliest or v > latest:
        raise ValueError(
            f"first_paycheck_date must be within {FIRST_PAYCHECK_MAX_DAYS_PAST} "
            f"days in the past and {FIRST_PAYCHECK_MAX_DAYS_FUTURE} days in "
            "the future"
        )
    return v


class PayScheduleCreate(BaseModel):
    net_salary: Decimal
    first_paycheck_date: date
    beginning_balance: Decimal
    frequency: PayFrequency

    @field_validator("net_salary")
    @classmethod
    def salary_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("net_salary must be greater than 0")
        return v

    @field_validator("beginning_balance")
    @classmethod
    def balance_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("beginning_balance must be 0 or greater")
        return v

    @field_validator("first_paycheck_date")
    @classmethod
    def paycheck_date_in_range(cls, v: date) -> date:
        return _validate_first_paycheck_date(v)


class PayScheduleUpdate(BaseModel):
    net_salary: Decimal | None = None
    first_paycheck_date: date | None = None
    beginning_balance: Decimal | None = None
    frequency: PayFrequency | None = None

    @field_validator("net_salary")
    @classmethod
    def salary_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("net_salary must be greater than 0")
        return v

    @field_validator("beginning_balance")
    @classmethod
    def balance_non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("beginning_balance must be 0 or greater")
        return v

    @field_validator("first_paycheck_date")
    @classmethod
    def paycheck_date_in_range(cls, v: date | None) -> date | None:
        if v is None:
            return v
        return _validate_first_paycheck_date(v)


class PayScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    net_salary: Decimal
    first_paycheck_date: date
    beginning_balance: Decimal
    frequency: PayFrequency
    created_at: datetime
    updated_at: datetime
