import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { downloadBudgetPdf, saveBlob } from "../src/api/reports";
import { ApiError } from "../src/api/client";

beforeEach(() => {
  vi.restoreAllMocks();
  // jsdom does not implement these object-URL helpers
  globalThis.URL.createObjectURL = vi.fn(() => "blob:mock");
  globalThis.URL.revokeObjectURL = vi.fn();
});

afterEach(() => vi.restoreAllMocks());

function mockPdfFetch(ok = true) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Server Error",
    blob: async () => new Blob(["%PDF-1.7"], { type: "application/pdf" }),
    headers: new Headers({
      "content-disposition": 'attachment; filename="budget-2025-01-03.pdf"',
    }),
  } as Response);
}

describe("saveBlob", () => {
  it("creates an object URL and clicks a download link", () => {
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    saveBlob(new Blob(["x"]), "file.pdf");
    expect(globalThis.URL.createObjectURL).toHaveBeenCalledOnce();
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledOnce();
  });
});

describe("downloadBudgetPdf", () => {
  it("fetches the budget PDF endpoint", async () => {
    const fetchMock = mockPdfFetch();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    await downloadBudgetPdf();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/reports/budget.pdf");
  });

  it("includes from/to query params when provided", async () => {
    const fetchMock = mockPdfFetch();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    await downloadBudgetPdf("2025-01-03", "2025-01-30");
    expect(fetchMock.mock.calls[0][0]).toContain("from=2025-01-03");
    expect(fetchMock.mock.calls[0][0]).toContain("to=2025-01-30");
  });

  it("triggers a file download on success", async () => {
    mockPdfFetch();
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    await downloadBudgetPdf();
    expect(clickSpy).toHaveBeenCalledOnce();
  });

  it("uses the filename from the content-disposition header", async () => {
    mockPdfFetch();
    let captured = "";
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      captured = this.download;
    });
    await downloadBudgetPdf();
    expect(captured).toBe("budget-2025-01-03.pdf");
  });

  it("throws an ApiError when the request fails", async () => {
    mockPdfFetch(false);
    await expect(downloadBudgetPdf()).rejects.toBeInstanceOf(ApiError);
  });
});
