import enum


class PayFrequency(enum.StrEnum):
    weekly = "weekly"
    biweekly = "biweekly"
    semimonthly = "semimonthly"
    monthly = "monthly"


class BillRecurrence(enum.StrEnum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    semiannual = "semiannual"
    annual = "annual"
    one_time = "one_time"


class BillCategory(enum.StrEnum):
    housing = "housing"
    utilities = "utilities"
    subscriptions = "subscriptions"
    insurance = "insurance"
    debt = "debt"
    savings = "savings"
    other = "other"


class BillStatus(enum.StrEnum):
    pending = "pending"
    paid = "paid"
    skipped = "skipped"
