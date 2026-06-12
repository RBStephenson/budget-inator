import { ApiError, get } from "./client";
import type { PayPeriodActual } from "../types/payPeriodActual";

const BASE = "/api";

export function listPayPeriodActuals(): Promise<PayPeriodActual[]> {
  return get<PayPeriodActual[]>("/pay-period-actuals");
}

export async function putPayPeriodActual(
  payDate: string,
  fields: { actualNetPay?: string; actualBalance?: string },
): Promise<void> {
  const body: Record<string, unknown> = {};
  if (fields.actualNetPay !== undefined) body.actual_net_pay = fields.actualNetPay;
  if (fields.actualBalance !== undefined) body.actual_balance = fields.actualBalance;

  const res = await fetch(`${BASE}/pay-period-actuals/${payDate}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
}
