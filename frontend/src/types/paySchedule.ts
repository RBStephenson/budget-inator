export type PayFrequency = "weekly" | "biweekly" | "semimonthly" | "monthly";

export const FREQUENCY_LABELS: Record<PayFrequency, string> = {
  weekly: "Weekly",
  biweekly: "Bi-weekly",
  semimonthly: "Semi-monthly (1st & 15th)",
  monthly: "Monthly",
};

export interface PaySchedule {
  id: number;
  net_salary: string;
  first_paycheck_date: string;
  beginning_balance: string;
  frequency: PayFrequency;
  created_at: string;
  updated_at: string;
}

export interface PayScheduleWrite {
  net_salary: string;
  first_paycheck_date: string;
  beginning_balance: string;
  frequency: PayFrequency;
}
