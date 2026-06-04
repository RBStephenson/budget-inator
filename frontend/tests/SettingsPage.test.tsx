import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SettingsPage } from "../src/components/SettingsPage";
import { makePaySchedule } from "./fixtures";

function mockFetch404() {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: false,
    status: 404,
    statusText: "Not Found",
    json: async () => ({}),
  } as Response);
}

function mockFetchOk(data: unknown) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => data,
  } as Response);
}

function mockFetchError() {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: false,
    status: 500,
    statusText: "Internal Server Error",
    json: async () => ({}),
  } as Response);
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("SettingsPage", () => {
  it("shows loading state initially", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    render(<SettingsPage />);
    expect(screen.getByText(/loading settings/i)).toBeInTheDocument();
  });

  it("shows error state when GET fails", async () => {
    mockFetchError();
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(/could not load settings/i)).toBeInTheDocument(),
    );
  });

  it("shows create form with intro text when no schedule exists", async () => {
    mockFetch404();
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(/enter your pay details/i)).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: /save and go to dashboard/i }),
    ).toBeInTheDocument();
  });

  it("shows edit form pre-populated when a schedule exists", async () => {
    mockFetchOk(makePaySchedule({ net_salary: "3500.00", beginning_balance: "800.00" }));
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument(),
    );
    expect(screen.queryByText(/enter your pay details/i)).not.toBeInTheDocument();
    expect((screen.getByLabelText(/net salary/i) as HTMLInputElement).value).toBe("3500");
    expect((screen.getByLabelText(/current balance/i) as HTMLInputElement).value).toBe("800");
  });

  it("shows validation errors when submitted with empty fields", async () => {
    mockFetch404();
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save and go to dashboard/i })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /save and go to dashboard/i }));
    expect(screen.getByText(/enter a salary greater than \$0/i)).toBeInTheDocument();
    expect(screen.getByText(/enter your current balance/i)).toBeInTheDocument();
    expect(screen.getByText(/select the date/i)).toBeInTheDocument();
  });

  it("POSTs to create a new schedule", async () => {
    const created = makePaySchedule();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({}),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => created,
      } as Response);

    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save and go to dashboard/i })).toBeInTheDocument(),
    );

    await userEvent.clear(screen.getByLabelText(/net salary/i));
    await userEvent.type(screen.getByLabelText(/net salary/i), "2000");
    await userEvent.clear(screen.getByLabelText(/current balance/i));
    await userEvent.type(screen.getByLabelText(/current balance/i), "500");
    await userEvent.type(screen.getByLabelText(/first paycheck date/i), "2025-01-03");
    await userEvent.click(screen.getByRole("button", { name: /save and go to dashboard/i }));

    await waitFor(() => {
      const calls = fetchSpy.mock.calls;
      const postCall = calls.find((c) => {
        const init = c[1] as RequestInit | undefined;
        return init?.method === "POST";
      });
      expect(postCall).toBeDefined();
    });
  });

  it("PATCHes to update an existing schedule", async () => {
    const existing = makePaySchedule();
    const updated = makePaySchedule({ net_salary: "2500.00" });
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => existing,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => updated,
      } as Response);

    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      const calls = fetchSpy.mock.calls;
      const patchCall = calls.find((c) => {
        const init = c[1] as RequestInit | undefined;
        return init?.method === "PATCH";
      });
      expect(patchCall).toBeDefined();
    });
  });

  it("shows saved confirmation after a successful save", async () => {
    const existing = makePaySchedule();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => existing,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => existing,
      } as Response);

    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));
    await waitFor(() =>
      expect(screen.getByText(/saved/i)).toBeInTheDocument(),
    );
  });

  it("shows error feedback when save fails", async () => {
    const existing = makePaySchedule();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => existing,
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: async () => ({}),
      } as Response);

    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));
    await waitFor(() =>
      expect(screen.getByText(/failed to save/i)).toBeInTheDocument(),
    );
  });
});
