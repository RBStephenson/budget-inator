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
  placement_source: "inferred" | "manual" | "paid";
  manual_pay_date: string | null;
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

export interface RebalanceMove {
  bill_id: number;
  name: string;
  due_date: string;
  amount: string;
  from_pay_date: string;
  to_pay_date: string;
  from_period_remaining_before: string;
  from_period_remaining_after: string;
  source_remaining_before: string;
  source_remaining_after: string;
  reason: string;
}

export interface RebalancePreview {
  source_pay_date: string;
  source_remaining_before: string;
  source_remaining_after: string;
  moves: RebalanceMove[];
}
