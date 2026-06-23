export interface AssignedBill {
  bill_id: number;
  name: string;
  due_date: string;
  amount: string;
  status: "on_time" | "late_flagged" | "paid" | "skipped";
  instance_id: number | null;
  actual_amount: string | null;
  is_variable: boolean;
  category: string;
  sinking_fund_applied: string;
  sinking_fund_shortfall: string;
}

export interface SinkingFundContribution {
  bill_id: number;
  name: string;
  next_due_date: string;
  target_amount: string;
  saved_amount: string;
  contribution_amount: string;
  shortfall_amount: string;
  surplus_amount: string;
}

export interface PayPeriod {
  period_index: number;
  pay_date: string;
  original_pay_date: string;
  is_overridden: boolean;
  period_start: string;
  period_end: string;
  opening_balance: string;
  total_bills: string;
  total_sinking_funds: string;
  remaining_balance: string;
  flagged_bill_count: number;
  assigned_bills: AssignedBill[];
  sinking_fund_contributions: SinkingFundContribution[];
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
