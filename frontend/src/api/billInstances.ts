import { get, patch } from "./client";

export type InstanceStatus = "paid" | "skipped" | "pending";

export interface BillInstance {
  id: number;
  bill_id: number;
  due_date: string;
  estimated_amount: string;
  actual_amount: string | null;
  status: InstanceStatus;
  paid_at: string | null;
  manual_pay_date: string | null;
}

export function listBillInstances(billId: number): Promise<BillInstance[]> {
  return get<BillInstance[]>(`/bill-instances/${billId}`);
}

export async function patchBillInstance(
  billId: number,
  dueDate: string,
  instanceStatus: InstanceStatus,
  actualAmount?: string,
  paidAt?: string,
  manualPayDate?: string | null,
): Promise<void> {
  const body: Record<string, unknown> = { status: instanceStatus };
  if (actualAmount !== undefined) body.actual_amount = actualAmount;
  // A YYYY-MM-DD date the backend coerces to a datetime; lets the user
  // back-date a payment. Only meaningful when marking paid.
  if (paidAt !== undefined) body.paid_at = paidAt;
  if (manualPayDate !== undefined) body.manual_pay_date = manualPayDate;

  return patch<void>(`/bill-instances/${billId}/${dueDate}`, body);
}
