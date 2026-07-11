import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SettingsPage } from "../src/components/SettingsPage";
import { ToastContainer } from "../src/components/ToastContainer";
import { ToastProvider } from "../src/context/ToastContext";
import * as router from "../src/router";
import { makePaySchedule } from "./fixtures";

function renderWithToast(ui: React.ReactElement) {
  return render(
    <ToastProvider>
      {ui}
      <ToastContainer />
    </ToastProvider>,
  );
}

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
    renderWithToast(<SettingsPage />);
    expect(screen.getByText(/loading settings/i)).toBeInTheDocument();
  });

  it("shows error state when GET fails", async () => {
    mockFetchError();
    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(/could not load settings/i)).toBeInTheDocument(),
    );
  });

  it("shows create form with intro text when no schedule exists", async () => {
    mockFetch404();
    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(/enter your pay details/i)).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: /save and go to dashboard/i }),
    ).toBeInTheDocument();
  });

  it("shows edit form pre-populated when a schedule exists", async () => {
    mockFetchOk(makePaySchedule({ net_salary: "3500.00", beginning_balance: "800.00" }));
    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument(),
    );
    expect(screen.queryByText(/enter your pay details/i)).not.toBeInTheDocument();
    expect((screen.getByLabelText(/net salary/i) as HTMLInputElement).value).toBe("3500");
    expect((screen.getByLabelText(/current balance/i) as HTMLInputElement).value).toBe("800");
  });

  it("explains how the semimonthly anchor selects the payday pattern", async () => {
    mockFetchOk(makePaySchedule({ frequency: "semimonthly" }));
    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument(),
    );
    expect(screen.getByText(/15th\/month-end schedule/i)).toBeInTheDocument();
  });

  it("shows validation errors when submitted with empty fields", async () => {
    mockFetch404();
    renderWithToast(<SettingsPage />);
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

    renderWithToast(<SettingsPage />);
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

    renderWithToast(<SettingsPage />);
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

  it("navigates to the dashboard after first-time setup (#86)", async () => {
    const created = makePaySchedule();
    vi.spyOn(globalThis, "fetch")
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
    const navSpy = vi.spyOn(router, "navigate").mockImplementation(() => {});

    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save and go to dashboard/i })).toBeInTheDocument(),
    );

    await userEvent.clear(screen.getByLabelText(/net salary/i));
    await userEvent.type(screen.getByLabelText(/net salary/i), "2000");
    await userEvent.clear(screen.getByLabelText(/current balance/i));
    await userEvent.type(screen.getByLabelText(/current balance/i), "500");
    await userEvent.type(screen.getByLabelText(/first paycheck date/i), "2025-01-03");
    await userEvent.click(screen.getByRole("button", { name: /save and go to dashboard/i }));

    await waitFor(() => expect(navSpy).toHaveBeenCalledWith("/"));
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

    renderWithToast(<SettingsPage />);
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

    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));
    await waitFor(() =>
      expect(screen.getByText(/failed to save/i)).toBeInTheDocument(),
    );
  });
});

describe("SettingsPage — data management", () => {
  function mockScheduleLoad() {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({}),
    } as Response);
  }

  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("renders export, import, and delete buttons", async () => {
    mockScheduleLoad();
    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /export/i })).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: /delete all data/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/import backup file/i)).toBeInTheDocument();
  });

  it("calls GET /api/data/export on export click", async () => {
    const blob = new Blob(['{"version":1}'], { type: "application/json" });
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
        blob: async () => blob,
      } as unknown as Response);

    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:mock"),
      revokeObjectURL: vi.fn(),
    });

    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /export backup/i })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /export backup/i }));
    await waitFor(() =>
      expect(fetchSpy.mock.calls.some((c) => String(c[0]).includes("/data/export"))).toBe(true),
    );
  });

  it("calls DELETE /api/data after confirming delete", async () => {
    mockScheduleLoad();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: false, status: 404, json: async () => ({}),
      } as Response)
      .mockResolvedValueOnce({
        ok: true, status: 204, json: async () => ({}),
      } as Response);

    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /delete all data/i })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /delete all data/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /delete everything/i }));
    await waitFor(() => {
      const deleteCall = fetchSpy.mock.calls.find(
        (c) => (c[1] as RequestInit | undefined)?.method === "DELETE",
      );
      expect(deleteCall).toBeDefined();
    });
    await waitFor(() =>
      expect(screen.getByText(/all data deleted/i)).toBeInTheDocument(),
    );
  });

  it("shows confirm dialog and cancel dismisses it", async () => {
    mockScheduleLoad();
    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /delete all data/i })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /delete all data/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("returns to the create form after deleting all data (#81)", async () => {
    // Load an existing schedule (edit mode), then delete all data.
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => makePaySchedule(),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
        statusText: "No Content",
        json: async () => ({}),
      } as Response);

    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /delete all data/i }));
    await userEvent.click(screen.getByRole("button", { name: /delete everything/i }));

    // After delete the form must switch back to create mode, so a subsequent
    // save POSTs a new schedule instead of PATCHing the deleted row (404).
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /save and go to dashboard/i }),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/enter your pay details/i)).toBeInTheDocument();
  });

  it("renders the danger zone as visually distinct from the other data rows", async () => {
    mockFetch404();
    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /delete all data/i })).toBeInTheDocument(),
    );

    const deleteButton = screen.getByRole("button", { name: /delete all data/i });
    const dangerRow = deleteButton.closest(".settings-data__item--danger");
    expect(dangerRow).not.toBeNull();
    expect(dangerRow).toHaveClass("settings-data__item--danger");
    expect(deleteButton).toHaveClass("btn--danger");
  });

  it("refreshes the form from re-fetched data after import (#81)", async () => {
    vi.spyOn(globalThis, "fetch")
      // initial load: no schedule yet
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({}),
      } as Response)
      // POST /api/data/import
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
        statusText: "No Content",
        json: async () => ({}),
      } as Response)
      // GET /api/pay-schedule re-fetch after import
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => makePaySchedule({ net_salary: "4242.00" }),
      } as Response);

    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /save and go to dashboard/i }),
      ).toBeInTheDocument(),
    );

    const backup = JSON.stringify({ version: 1 });
    const file = new File([backup], "backup.json", { type: "application/json" });
    // jsdom's File doesn't implement text(); browsers do. Provide it so
    // handleImport can read the upload.
    Object.defineProperty(file, "text", { value: () => Promise.resolve(backup) });
    await userEvent.upload(screen.getByLabelText(/import backup file/i), file);

    await waitFor(() =>
      expect((screen.getByLabelText(/net salary/i) as HTMLInputElement).value).toBe("4242"),
    );
    // Re-fetched schedule means the page is now in edit mode.
    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });

  it("treats an imported backup without a schedule as successful", async () => {
    vi.spyOn(globalThis, "fetch")
      // initial load: no schedule yet
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({}),
      } as Response)
      // POST /api/data/import
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
        statusText: "No Content",
        json: async () => ({}),
      } as Response)
      // GET /api/pay-schedule re-fetch after import: backup had no schedule
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({}),
      } as Response);

    renderWithToast(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /save and go to dashboard/i }),
      ).toBeInTheDocument(),
    );

    const backup = JSON.stringify({ version: 6, bills: [] });
    const file = new File([backup], "empty-backup.json", { type: "application/json" });
    Object.defineProperty(file, "text", { value: () => Promise.resolve(backup) });
    await userEvent.upload(screen.getByLabelText(/import backup file/i), file);

    await waitFor(() => expect(screen.getByText(/imported/i)).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: /save and go to dashboard/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/not found/i)).not.toBeInTheDocument();
  });
});
