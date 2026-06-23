import type { AssignedBill, PayPeriod, ScheduleResponse } from "../src/types/schedule";
import type { Bill } from "../src/types/bill";
import type { PaySchedule } from "../src/types/paySchedule";
import type { MonthlySummary, MonthlyCategoryGroup, MonthlyBillItem } from "../src/types/monthly";

export function makeBill(overrides: Partial<AssignedBill> = {}): AssignedBill {
  return {
    bill_id: 1,
    name: "Rent",
    due_date: "2025-01-15",
    amount: "1200.00",
    status: "on_time",
    instance_id: null,
    actual_amount: null,
    is_variable: false,
    category: "housing",
    ...overrides,
  };
}

export function makePeriod(overrides: Partial<PayPeriod> = {}): PayPeriod {
  return {
    period_index: 0,
    pay_date: "2025-01-03",
    original_pay_date: "2025-01-03",
    is_overridden: false,
    period_start: "2025-01-03",
    period_end: "2025-01-16",
    opening_balance: "1500.00",
    total_bills: "1200.00",
    remaining_balance: "300.00",
    flagged_bill_count: 0,
    assigned_bills: [],
    ...overrides,
  };
}

export function makeApiBill(overrides: Partial<Bill> = {}): Bill {
  return {
    id: 1,
    name: "Rent",
    amount: "1200.00",
    recurrence: "monthly",
    due_day: 1,
    due_day_is_month_end: false,
    due_date: null,
    grace_period_days: 0,
    category: "housing",
    is_variable: false,
    is_active: true,
    notes: null,
    created_at: "2025-01-01T00:00:00",
    updated_at: "2025-01-01T00:00:00",
    ...overrides,
  };
}

export function makePaySchedule(overrides: Partial<PaySchedule> = {}): PaySchedule {
  return {
    id: 1,
    net_salary: "2000.00",
    first_paycheck_date: "2025-01-03",
    beginning_balance: "500.00",
    frequency: "biweekly",
    created_at: "2025-01-01T00:00:00",
    updated_at: "2025-01-01T00:00:00",
    ...overrides,
  };
}

export function makeSchedule(
  periods: PayPeriod[] = [makePeriod()],
): ScheduleResponse {
  return {
    periods,
    summary: {
      from_date: periods[0]?.period_start ?? "2025-01-03",
      to_date: periods[periods.length - 1]?.period_end ?? "2025-01-16",
      period_count: periods.length,
      total_flagged_bills: periods.reduce((n, p) => n + p.flagged_bill_count, 0),
    },
  };
}

export function makeMonthlyBillItem(
  overrides: Partial<MonthlyBillItem> = {},
): MonthlyBillItem {
  return {
    bill_id: 1,
    name: "Rent",
    due_date: "2025-01-01",
    amount: "900.00",
    category: "housing",
    is_variable: false,
    status: "on_time",
    actual_amount: null,
    ...overrides,
  };
}

export function makeMonthlyCategoryGroup(
  overrides: Partial<MonthlyCategoryGroup> = {},
): MonthlyCategoryGroup {
  return {
    category: "housing",
    subtotal: "900.00",
    bills: [makeMonthlyBillItem()],
    ...overrides,
  };
}

export function makeMonthlySummary(
  overrides: Partial<MonthlySummary> = {},
): MonthlySummary {
  return {
    month: "2025-01",
    total_income: "2000.00",
    total_bills: "900.00",
    available: "1100.00",
    categories: [makeMonthlyCategoryGroup()],
    ...overrides,
  };
}
