import enum


class PayFrequency(str, enum.Enum):
    weekly = "weekly"
    biweekly = "biweekly"
    semimonthly = "semimonthly"
    monthly = "monthly"


class BillRecurrence(str, enum.Enum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    semiannual = "semiannual"
    annual = "annual"
    one_time = "one_time"


class BillCategory(str, enum.Enum):
    housing = "housing"
    utilities = "utilities"
    subscriptions = "subscriptions"
    insurance = "insurance"
    debt = "debt"
    savings = "savings"
    other = "other"


class BillStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    skipped = "skipped"
