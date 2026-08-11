import { describe, it, expect, vi, beforeEach } from "vitest";
import { ApiError, get, post, patch, put, del } from "../src/api/client";

beforeEach(() => vi.restoreAllMocks());

function mockFetch(status: number, body?: unknown, statusText = "Error"): void {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: async () => body,
    blob: async () => new Blob(),
  } as Response);
}

describe("ApiError detail extraction", () => {
  it("uses FastAPI detail string when present", async () => {
    mockFetch(422, { detail: "amount must be positive" });
    await expect(get("/bills")).rejects.toMatchObject({
      message: "amount must be positive",
      status: 422,
    });
  });

  it("falls back to status text when detail is absent", async () => {
    mockFetch(500, {}, "Internal Server Error");
    await expect(get("/bills")).rejects.toMatchObject({
      message: "500 Internal Server Error",
    });
  });

  it("falls back to status text when body is not JSON", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 503,
      statusText: "Service Unavailable",
      json: async () => { throw new SyntaxError("not json"); },
    } as unknown as Response);
    await expect(get("/bills")).rejects.toMatchObject({
      message: "503 Service Unavailable",
    });
  });

  it("throws ApiError (not plain Error)", async () => {
    mockFetch(404, { detail: "not found" });
    await expect(get("/bills")).rejects.toBeInstanceOf(ApiError);
  });

  it("formats FastAPI's array-of-errors detail (real 422 shape) into fieldErrors", async () => {
    mockFetch(422, {
      detail: [
        { loc: ["body", "bills", 0, "amount"], msg: "must be greater than 0" },
        { loc: ["body", "bills", 0, "due_day"], msg: "must be between 1 and 31" },
      ],
    });
    await expect(get("/bills")).rejects.toMatchObject({
      status: 422,
      fieldErrors: [
        "bills.0.amount: must be greater than 0",
        "bills.0.due_day: must be between 1 and 31",
      ],
      message: "bills.0.amount: must be greater than 0; bills.0.due_day: must be between 1 and 31",
    });
  });

  it("handles an array detail entry with no loc", async () => {
    mockFetch(422, { detail: [{ msg: "payload must be an object" }] });
    await expect(get("/bills")).rejects.toMatchObject({
      fieldErrors: ["payload must be an object"],
    });
  });

  it("defaults fieldErrors to an empty array for a string detail", async () => {
    mockFetch(400, { detail: "name required" });
    await expect(get("/bills")).rejects.toMatchObject({ fieldErrors: [] });
  });
});

describe("post", () => {
  it("sends JSON body and returns parsed response", async () => {
    mockFetch(200, { id: 1, name: "Rent" });
    const result = await post<{ id: number; name: string }>("/bills", { name: "Rent" });
    expect(result).toEqual({ id: 1, name: "Rent" });
  });

  it("returns undefined on 204", async () => {
    mockFetch(204);
    const result = await post<void>("/bills", {});
    expect(result).toBeUndefined();
  });

  it("throws with FastAPI detail on error", async () => {
    mockFetch(400, { detail: "name required" });
    await expect(post("/bills", {})).rejects.toMatchObject({ message: "name required" });
  });
});

describe("patch", () => {
  it("throws with detail on error", async () => {
    mockFetch(422, { detail: "invalid recurrence" });
    await expect(patch("/bills/1", {})).rejects.toMatchObject({
      message: "invalid recurrence",
      status: 422,
    });
  });
});

describe("put", () => {
  it("returns undefined on 204", async () => {
    mockFetch(204);
    const result = await put<void>("/overrides/2025-01-01", {});
    expect(result).toBeUndefined();
  });
});

describe("del", () => {
  it("resolves without error on success", async () => {
    mockFetch(204);
    await expect(del("/data")).resolves.toBeUndefined();
  });

  it("throws ApiError on failure", async () => {
    mockFetch(403, { detail: "forbidden" });
    await expect(del("/data")).rejects.toBeInstanceOf(ApiError);
  });
});
