import { get } from "./client";
import type { Bill, BillCreate, BillUpdate } from "../types/bill";

const BASE = "/api";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export function listBills(): Promise<Bill[]> {
  return get<Bill[]>("/bills");
}

export function createBill(data: BillCreate): Promise<Bill> {
  return post<Bill>("/bills", data);
}

export function updateBill(id: number, data: BillUpdate): Promise<Bill> {
  return patch<Bill>(`/bills/${id}`, data);
}

export function deactivateBill(id: number): Promise<Bill> {
  return patch<Bill>(`/bills/${id}`, { is_active: false });
}
