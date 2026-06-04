import type { AssignedBill, PayPeriod, ScheduleResponse } from "../src/types/schedule";

export function makeBill(overrides: Partial<AssignedBill> = {}): AssignedBill {
  return {
    bill_id: 1,
    name: "Rent",
    due_date: "2025-01-15",
    amount: "1200.00",
    status: "on_time",
    ...overrides,
  };
}

export function makePeriod(overrides: Partial<PayPeriod> = {}): PayPeriod {
  return {
    period_index: 0,
    pay_date: "2025-01-03",
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
