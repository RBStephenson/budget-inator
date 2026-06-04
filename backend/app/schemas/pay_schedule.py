from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import PayFrequency


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


class PayScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    net_salary: Decimal
    first_paycheck_date: date
    beginning_balance: Decimal
    frequency: PayFrequency
    created_at: datetime
    updated_at: datetime
