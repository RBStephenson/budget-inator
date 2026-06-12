import { ApiError } from "./client";

const BASE = "/api";

export type InstanceStatus = "paid" | "skipped" | "pending";

export async function patchBillInstance(
  billId: number,
  dueDate: string,
  instanceStatus: InstanceStatus,
  actualAmount?: string,
  paidAt?: string,
): Promise<void> {
  const body: Record<string, unknown> = { status: instanceStatus };
  if (actualAmount !== undefined) body.actual_amount = actualAmount;
  // A YYYY-MM-DD date the backend coerces to a datetime; lets the user
  // back-date a payment. Only meaningful when marking paid.
  if (paidAt !== undefined) body.paid_at = paidAt;

  const res = await fetch(`${BASE}/bill-instances/${billId}/${dueDate}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
}
