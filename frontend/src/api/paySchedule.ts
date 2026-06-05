import { ApiError, get } from "./client";
import type { PaySchedule, PayScheduleWrite } from "../types/paySchedule";

const BASE = "/api";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export async function getPaySchedule(): Promise<PaySchedule | null> {
  try {
    return await get<PaySchedule>("/pay-schedule");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export function createPaySchedule(data: PayScheduleWrite): Promise<PaySchedule> {
  return post<PaySchedule>("/pay-schedule", data);
}

export function updatePaySchedule(data: Partial<PayScheduleWrite>): Promise<PaySchedule> {
  return patch<PaySchedule>("/pay-schedule", data);
}
