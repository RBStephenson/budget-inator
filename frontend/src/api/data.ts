import { ApiError, post, del } from "./client";

const BASE = "/api";

export interface ImportPreviewSchedule {
  net_salary: string;
  frequency: string;
  first_paycheck_date: string;
}

export interface ImportPreview {
  pay_schedule: ImportPreviewSchedule | null;
  bill_count: number;
  bill_instance_count: number;
  bill_version_count: number;
  pay_period_override_count: number;
  pay_period_actual_count: number;
}

export async function exportData(): Promise<Blob> {
  // Raw fetch: returns Blob, not JSON — can't use the shared helpers.
  const res = await fetch(`${BASE}/data/export`);
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  return res.blob();
}

export function previewImport(payload: unknown): Promise<ImportPreview> {
  return post<ImportPreview>("/data/import/preview", payload);
}

export function importData(payload: unknown): Promise<void> {
  return post<void>("/data/import", payload);
}

export function deleteAllData(): Promise<void> {
  return del("/data");
}
