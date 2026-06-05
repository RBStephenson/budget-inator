import { get } from "./client";
import type { MonthlySummaryResponse } from "../types/monthly";

export async function fetchMonthlySummary(
  from?: string,
  to?: string,
): Promise<MonthlySummaryResponse> {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  const query = params.size > 0 ? `?${params}` : "";
  return get<MonthlySummaryResponse>(`/schedule/monthly-summary${query}`);
}
