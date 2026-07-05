import { post } from "./client";
import type { RebalanceMove, RebalancePreview } from "../types/schedule";

export function previewRebalance(
  sourcePayDate: string,
): Promise<RebalancePreview> {
  return post<RebalancePreview>("/schedule/rebalance-preview", {
    source_pay_date: sourcePayDate,
  });
}

export function applyRebalance(moves: RebalanceMove[]): Promise<void> {
  return post<void>("/schedule/rebalance-apply", { moves });
}
