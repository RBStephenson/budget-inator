import { ApiError, post, del } from "./client";

const BASE = "/api";

export async function exportData(): Promise<Blob> {
  // Raw fetch: returns Blob, not JSON — can't use the shared helpers.
  const res = await fetch(`${BASE}/data/export`);
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  return res.blob();
}

export function importData(payload: unknown): Promise<void> {
  return post<void>("/data/import", payload);
}

export function deleteAllData(): Promise<void> {
  return del("/data");
}
