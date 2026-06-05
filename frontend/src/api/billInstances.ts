import { ApiError } from "./client";

const BASE = "/api";

export type InstanceStatus = "paid" | "skipped" | "pending";

export async function patchBillInstance(
  billId: number,
  dueDate: string,
  instanceStatus: InstanceStatus,
  actualAmount?: string,
): Promise<void> {
  const body: Record<string, unknown> = { status: instanceStatus };
  if (actualAmount !== undefined) body.actual_amount = actualAmount;

  const res = await fetch(`${BASE}/bill-instances/${billId}/${dueDate}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
}
