import { put, del } from "./client";

export async function putPayPeriodOverride(
  originalDate: string,
  overrideDate: string,
): Promise<void> {
  return put<void>(`/pay-period-overrides/${originalDate}`, { override_date: overrideDate });
}

export async function deletePayPeriodOverride(originalDate: string): Promise<void> {
  return del(`/pay-period-overrides/${originalDate}`);
}
