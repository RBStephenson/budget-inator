export interface AssignedBill {
  bill_id: number;
  name: string;
  due_date: string;
  amount: string;
  status: "on_time" | "late_flagged" | "paid" | "skipped";
  instance_id: number | null;
  actual_amount: string | null;
  is_variable: boolean;
}

export interface PayPeriod {
  period_index: number;
  pay_date: string;
  period_start: string;
  period_end: string;
  opening_balance: string;
  total_bills: string;
  remaining_balance: string;
  flagged_bill_count: number;
  assigned_bills: AssignedBill[];
}

export interface ScheduleSummary {
  from_date: string;
  to_date: string;
  period_count: number;
  total_flagged_bills: number;
}

export interface ScheduleResponse {
  periods: PayPeriod[];
  summary: ScheduleSummary;
}
