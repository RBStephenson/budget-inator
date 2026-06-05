import { ApiError } from "./client";

const BASE = "/api";

export async function putPayPeriodOverride(
  originalDate: string,
  overrideDate: string,
): Promise<void> {
  const res = await fetch(`${BASE}/pay-period-overrides/${originalDate}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ override_date: overrideDate }),
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
}

export async function deletePayPeriodOverride(originalDate: string): Promise<void> {
  const res = await fetch(`${BASE}/pay-period-overrides/${originalDate}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
}
