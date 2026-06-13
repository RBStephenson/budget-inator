import { get, post, patch } from "./client";
import type { Bill, BillCreate, BillUpdate } from "../types/bill";

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
