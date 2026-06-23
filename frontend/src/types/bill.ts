export type BillRecurrence =
  | "monthly"
  | "biweekly"
  | "weekly"
  | "quarterly"
  | "semiannual"
  | "annual"
  | "one_time";

export type BillCategory =
  | "housing"
  | "utilities"
  | "subscriptions"
  | "insurance"
  | "debt"
  | "savings"
  | "other";

export interface Bill {
  id: number;
  name: string;
  amount: string;
  recurrence: BillRecurrence;
  due_day: number | null;
  due_day_is_month_end: boolean;
  due_date: string | null;
  grace_period_days: number;
  category: BillCategory;
  is_variable: boolean;
  sinking_fund_enabled: boolean;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface BillCreate {
  name: string;
  amount: string;
  recurrence: BillRecurrence;
  due_day?: number | null;
  due_day_is_month_end?: boolean;
  due_date?: string | null;
  grace_period_days?: number;
  category: BillCategory;
  is_variable?: boolean;
  sinking_fund_enabled?: boolean;
  notes?: string | null;
}

export interface BillUpdate {
  effective_date?: string | null;
  name?: string;
  amount?: string;
  recurrence?: BillRecurrence;
  due_day?: number | null;
  due_day_is_month_end?: boolean;
  due_date?: string | null;
  grace_period_days?: number;
  category?: BillCategory;
  is_variable?: boolean;
  sinking_fund_enabled?: boolean;
  is_active?: boolean;
  notes?: string | null;
}

export const RECURRENCE_LABELS: Record<BillRecurrence, string> = {
  monthly: "Monthly",
  biweekly: "Bi-weekly",
  weekly: "Weekly",
  quarterly: "Quarterly",
  semiannual: "Semi-annual",
  annual: "Annual",
  one_time: "One-time",
};

export const CATEGORY_ORDER: BillCategory[] = [
  "housing",
  "utilities",
  "subscriptions",
  "insurance",
  "debt",
  "savings",
  "other",
];

export const CATEGORY_LABELS: Record<BillCategory, string> = {
  housing: "Housing",
  utilities: "Utilities",
  subscriptions: "Subscriptions",
  insurance: "Insurance",
  debt: "Debt",
  savings: "Savings",
  other: "Other",
};

export const ANNUAL_MULTIPLIERS: Record<BillRecurrence, number> = {
  monthly: 12,
  biweekly: 26,
  weekly: 52,
  quarterly: 4,
  semiannual: 2,
  annual: 1,
  one_time: 1,
};

export function annualCost(bill: Pick<Bill, "amount" | "recurrence">): number {
  return parseFloat(bill.amount) * ANNUAL_MULTIPLIERS[bill.recurrence];
}
