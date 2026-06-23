from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import BillCategory, BillRecurrence


class BillCreate(BaseModel):
    name: str
    amount: Decimal
    recurrence: BillRecurrence
    due_day: int | None = None
    due_day_is_month_end: bool = False
    due_date: date | None = None
    grace_period_days: int = Field(default=0, ge=0)
    category: BillCategory
    is_variable: bool = False
    sinking_fund_enabled: bool = False
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("due_day")
    @classmethod
    def due_day_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 31):
            raise ValueError("due_day must be between 1 and 31")
        return v

    @model_validator(mode="after")
    def due_date_rules(self) -> BillCreate:
        if self.recurrence == BillRecurrence.monthly:
            if self.due_day_is_month_end and self.due_day is not None:
                raise ValueError(
                    "due_day must be omitted when due_day_is_month_end is true"
                )
            if not self.due_day_is_month_end and self.due_day is None:
                raise ValueError(
                    "due_day is required unless due_day_is_month_end is true"
                )
            if self.due_date is not None:
                raise ValueError("due_date must be omitted for monthly recurrence")
        else:
            if self.due_date is None:
                raise ValueError("due_date is required for non-monthly recurrence")
            if self.due_day is not None:
                raise ValueError("due_day must be omitted for non-monthly recurrence")
            if self.due_day_is_month_end:
                raise ValueError(
                    "due_day_is_month_end must be false for non-monthly recurrence"
                )
        return self


class BillUpdate(BaseModel):
    effective_date: date | None = None
    name: str | None = None
    amount: Decimal | None = None
    recurrence: BillRecurrence | None = None
    due_day: int | None = None
    due_day_is_month_end: bool | None = None
    due_date: date | None = None
    grace_period_days: int | None = Field(default=None, ge=0)
    category: BillCategory | None = None
    is_variable: bool | None = None
    sinking_fund_enabled: bool | None = None
    is_active: bool | None = None
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("due_day")
    @classmethod
    def due_day_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 31):
            raise ValueError("due_day must be between 1 and 31")
        return v


class BillRead(BaseModel):
    # validation_alias: read estimated_amount/first_due_date from ORM but
    # serialize as amount/due_date in JSON responses
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    amount: Decimal = Field(validation_alias="estimated_amount")
    recurrence: BillRecurrence
    due_day: int | None
    due_day_is_month_end: bool
    due_date: date | None = Field(validation_alias="first_due_date")
    grace_period_days: int
    category: BillCategory
    is_variable: bool
    sinking_fund_enabled: bool
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
