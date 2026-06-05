export interface MonthlyBillItem {
  bill_id: number;
  name: string;
  due_date: string;
  amount: string;
  category: string;
  is_variable: boolean;
  status: "on_time" | "paid" | "skipped";
  actual_amount: string | null;
}

export interface MonthlyCategoryGroup {
  category: string;
  subtotal: string;
  bills: MonthlyBillItem[];
}

export interface MonthlySummary {
  month: string; // "YYYY-MM"
  total_income: string;
  total_bills: string;
  available: string;
  categories: MonthlyCategoryGroup[];
}

export interface MonthlySummaryResponse {
  months: MonthlySummary[];
}
