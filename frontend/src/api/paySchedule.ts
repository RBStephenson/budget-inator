import { ApiError, get, post, patch } from "./client";
import type { PaySchedule, PayScheduleWrite } from "../types/paySchedule";

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
