import { ApiError } from "./client";

const BASE = "/api";

function parseFilename(disposition: string | null): string | null {
  if (!disposition) return null;
  const match = /filename="?([^"]+)"?/.exec(disposition);
  return match ? match[1] : null;
}

/** Save a blob to disk by triggering a temporary download link. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Fetch the budget PDF for the given range and trigger a browser download. */
export async function downloadBudgetPdf(from?: string, to?: string): Promise<void> {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  const query = params.size > 0 ? `?${params}` : "";

  const res = await fetch(`${BASE}/reports/budget.pdf${query}`);
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);

  const blob = await res.blob();
  const filename =
    parseFilename(res.headers.get("content-disposition")) ?? "budget.pdf";
  saveBlob(blob, filename);
}
