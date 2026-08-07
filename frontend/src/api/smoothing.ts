import { post } from "./client";
import type { RebalancePreview } from "../types/schedule";

export function previewSmoothing(
  sourcePayDate: string,
): Promise<RebalancePreview> {
  return post<RebalancePreview>("/schedule/smoothing-preview", {
    source_pay_date: sourcePayDate,
  });
}
