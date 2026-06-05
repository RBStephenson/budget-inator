import { ApiError } from "./client";

const BASE = "/api";

export async function exportData(): Promise<Blob> {
  const res = await fetch(`${BASE}/data/export`);
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  return res.blob();
}

export async function importData(payload: unknown): Promise<void> {
  const res = await fetch(`${BASE}/data/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
}

export async function deleteAllData(): Promise<void> {
  const res = await fetch(`${BASE}/data`, { method: "DELETE" });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
}
