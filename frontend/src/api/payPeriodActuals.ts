import { get, put } from "./client";
import type { PayPeriodActual } from "../types/payPeriodActual";

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
  return put<void>(`/pay-period-actuals/${payDate}`, body);
}
