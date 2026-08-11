import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BillFormModal } from "../src/components/BillFormModal";
import { ToastContainer } from "../src/components/ToastContainer";
import { ToastProvider } from "../src/context/ToastContext";
import { makeApiBill } from "./fixtures";

function renderWithToast(ui: React.ReactElement) {
  return render(
    <ToastProvider>
      {ui}
      <ToastContainer />
    </ToastProvider>,
  );
}

function mockFetch(ok = true) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 201 : 422,
    statusText: ok ? "Created" : "Unprocessable Entity",
    json: async () => makeApiBill(),
  } as Response);
}

beforeEach(() => vi.restoreAllMocks());

describe("BillFormModal — add mode", () => {
  it("renders the add bill title", () => {
    renderWithToast(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Add bill" })).toBeInTheDocument();
  });

  it("shows the due-day field by default (monthly recurrence)", () => {
    renderWithToast(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    expect(screen.getByLabelText(/due day/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/due date/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/last day of month/i)).not.toBeChecked();
  });

  it("switches to due-date field when recurrence changes to biweekly", async () => {
    renderWithToast(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Bi-weekly" }));
    expect(screen.queryByLabelText(/due day/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/next due date/i)).toBeInTheDocument();
  });

  it("shows validation errors when submitting an empty form", async () => {
    renderWithToast(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /add bill/i }));
    expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/enter a positive amount/i)).toBeInTheDocument();
    expect(screen.getByText(/category is required/i)).toBeInTheDocument();
  });

  it("calls onSave after a successful submit", async () => {
    mockFetch(true);
    const onSave = vi.fn();
    renderWithToast(<BillFormModal onSave={onSave} onClose={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/^name/i), "Rent");
    await userEvent.type(screen.getByLabelText(/^amount/i), "1200");
    await userEvent.selectOptions(screen.getByLabelText(/category/i), "housing");
    await userEvent.type(screen.getByLabelText(/due day/i), "1");
    await userEvent.click(screen.getByRole("button", { name: /add bill/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
  });

  it("accepts the 31st as a fixed monthly due day", async () => {
    mockFetch(true);
    const onSave = vi.fn();
    renderWithToast(<BillFormModal onSave={onSave} onClose={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/^name/i), "Mortgage");
    await userEvent.type(screen.getByLabelText(/^amount/i), "1200");
    await userEvent.selectOptions(screen.getByLabelText(/category/i), "housing");
    await userEvent.type(screen.getByLabelText(/due day/i), "31");
    await userEvent.click(screen.getByRole("button", { name: /add bill/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: expect.stringContaining('"due_day":31'),
      }),
    );
  });

  it("submits an explicit last-day-of-month rule", async () => {
    mockFetch(true);
    const onSave = vi.fn();
    renderWithToast(<BillFormModal onSave={onSave} onClose={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/^name/i), "Mortgage");
    await userEvent.type(screen.getByLabelText(/^amount/i), "1200");
    await userEvent.selectOptions(screen.getByLabelText(/category/i), "housing");
    await userEvent.click(screen.getByLabelText(/last day of month/i));
    expect(screen.getByLabelText(/due day/i)).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /add bill/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
    const request = vi.mocked(globalThis.fetch).mock.calls[0][1] as RequestInit;
    expect(JSON.parse(request.body as string)).toMatchObject({
      due_day: null,
      due_day_is_month_end: true,
    });
  });

  it("calls onClose when cancel is clicked", async () => {
    const onClose = vi.fn();
    renderWithToast(<BillFormModal onSave={vi.fn()} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("shows the estimated label when is_variable is toggled on", async () => {
    renderWithToast(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    await userEvent.click(screen.getByLabelText(/variable amount/i));
    expect(screen.getByText("(estimated)")).toBeInTheDocument();
  });

  it("submits the sinking fund opt-in", async () => {
    mockFetch(true);
    const onSave = vi.fn();
    renderWithToast(<BillFormModal onSave={onSave} onClose={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/^name/i), "Insurance");
    await userEvent.type(screen.getByLabelText(/^amount/i), "1200");
    await userEvent.selectOptions(screen.getByLabelText(/category/i), "insurance");
    await userEvent.click(screen.getByRole("button", { name: "Annual" }));
    await userEvent.type(screen.getByLabelText(/next due date/i), "2025-03-01");
    await userEvent.click(screen.getByLabelText(/build a sinking fund/i));
    await userEvent.click(screen.getByRole("button", { name: /add bill/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
    const request = vi.mocked(globalThis.fetch).mock.calls[0][1] as RequestInit;
    expect(JSON.parse(request.body as string)).toMatchObject({
      sinking_fund_enabled: true,
    });
  });
});

describe("BillFormModal — duplicate mode", () => {
  it("renders the add bill title, not edit", () => {
    renderWithToast(
      <BillFormModal
        duplicateFrom={makeApiBill({ name: "Netflix" })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: "Add bill" })).toBeInTheDocument();
  });

  it("pre-fills the name with a Copy of prefix", () => {
    renderWithToast(
      <BillFormModal
        duplicateFrom={makeApiBill({ name: "Netflix" })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByDisplayValue("Copy of Netflix")).toBeInTheDocument();
  });

  it("pre-fills amount, category, and recurrence from the source bill", () => {
    renderWithToast(
      <BillFormModal
        duplicateFrom={makeApiBill({
          amount: "15.99",
          category: "subscriptions",
          recurrence: "monthly",
          due_day: 10,
        })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByDisplayValue("15.99")).toBeInTheDocument();
    expect((screen.getByLabelText(/category/i) as HTMLSelectElement).value).toBe(
      "subscriptions",
    );
    expect(screen.getByLabelText(/due day/i)).toHaveValue(10);
  });

  it("saves as a new bill via POST, not a PATCH to the source bill", async () => {
    mockFetch(true);
    const onSave = vi.fn();
    renderWithToast(
      <BillFormModal
        duplicateFrom={makeApiBill({ id: 42, name: "Netflix" })}
        onSave={onSave}
        onClose={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /add bill/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
    const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0];
    expect(init).toMatchObject({ method: "POST" });
    expect(String(url)).not.toContain("/42");
    expect(JSON.parse((init as RequestInit).body as string)).toMatchObject({
      name: "Copy of Netflix",
    });
  });
});

describe("BillFormModal — edit mode", () => {
  it("renders the edit bill title", () => {
    renderWithToast(
      <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { name: "Edit bill" })).toBeInTheDocument();
  });

  it("pre-fills the name field", () => {
    renderWithToast(
      <BillFormModal
        bill={makeApiBill({ name: "Mortgage" })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByDisplayValue("Mortgage")).toBeInTheDocument();
  });

  it("shows an effective date for forward-looking edits", () => {
    renderWithToast(
      <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
    );
    expect(screen.getByLabelText(/effective date/i)).toBeInTheDocument();
    expect(screen.getByText(/from this date forward/i)).toBeInTheDocument();
    expect(screen.getByText(/correct one occurrence/i)).toBeInTheDocument();
  });

  it("pre-fills the effective date using local time, not UTC (BI-24)", () => {
    // 7:30pm Central on Aug 4 is already Aug 5 in UTC — the default must
    // stay on the local day or the edit silently misses today's period.
    vi.stubEnv("TZ", "America/Chicago");
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-05T01:30:00Z"));
    try {
      renderWithToast(
        <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
      );
      expect(screen.getByLabelText(/effective date/i)).toHaveValue("2026-08-04");
    } finally {
      vi.useRealTimers();
      vi.unstubAllEnvs();
    }
  });

  it("sends the selected effective date when editing", async () => {
    mockFetch(true);
    const onSave = vi.fn();
    renderWithToast(
      <BillFormModal bill={makeApiBill()} onSave={onSave} onClose={vi.fn()} />,
    );
    const effectiveDate = screen.getByLabelText(/effective date/i);
    await userEvent.clear(effectiveDate);
    await userEvent.type(effectiveDate, "2025-02-01");
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
    const request = vi.mocked(globalThis.fetch).mock.calls[0][1] as RequestInit;
    expect(JSON.parse(request.body as string)).toMatchObject({
      effective_date: "2025-02-01",
    });
  });

  it("pre-fills the category dropdown", () => {
    renderWithToast(
      <BillFormModal
        bill={makeApiBill({ category: "housing" })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(
      (screen.getByLabelText(/category/i) as HTMLSelectElement).value,
    ).toBe("housing");
  });

  it("shows the due-date field when editing a biweekly bill", () => {
    renderWithToast(
      <BillFormModal
        bill={makeApiBill({ recurrence: "biweekly", due_day: null, due_date: "2025-01-03" })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByLabelText(/due date/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/due day/i)).not.toBeInTheDocument();
  });

  it("pre-fills an explicit month-end rule", () => {
    renderWithToast(
      <BillFormModal
        bill={makeApiBill({
          due_day: null,
          due_day_is_month_end: true,
        })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByLabelText(/last day of month/i)).toBeChecked();
    expect(screen.getByLabelText(/due day/i)).toBeDisabled();
  });

  it("shows a server error when the API call fails", async () => {
    mockFetch(false);
    renderWithToast(
      <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));
    await waitFor(() =>
      expect(screen.getByText(/failed to save bill/i)).toBeInTheDocument(),
    );
  });
});

function mockInstancesFetch(instances: unknown[], ok = true) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Internal Server Error",
    json: async () => instances,
  } as Response);
}

describe("BillFormModal — payment history", () => {
  it("does not show a payment history section in add mode", () => {
    renderWithToast(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    expect(screen.queryByText(/payment history/i)).not.toBeInTheDocument();
  });

  it("does not show a payment history section in duplicate mode", () => {
    renderWithToast(
      <BillFormModal
        duplicateFrom={makeApiBill({ name: "Netflix" })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByText(/payment history/i)).not.toBeInTheDocument();
  });

  it("is collapsed by default in edit mode and does not fetch until expanded", () => {
    mockInstancesFetch([]);
    renderWithToast(
      <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
    );
    expect(screen.getByText(/payment history/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("fetches and renders history rows when expanded", async () => {
    mockInstancesFetch([
      {
        id: 1,
        bill_id: 1,
        due_date: "2025-02-01",
        estimated_amount: "80.00",
        actual_amount: "75.00",
        status: "paid",
        paid_at: "2025-02-02T00:00:00",
        manual_pay_date: null,
      },
    ]);
    renderWithToast(
      <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
    );
    await userEvent.click(screen.getByText(/payment history/i));
    await waitFor(() => screen.getByRole("table"));
    const table = within(screen.getByRole("table"));
    expect(table.getByText("Paid")).toBeInTheDocument();
    expect(table.getByText("$75.00")).toBeInTheDocument();
  });

  it("shows an empty state when a bill has no payment history", async () => {
    mockInstancesFetch([]);
    renderWithToast(
      <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
    );
    await userEvent.click(screen.getByText(/payment history/i));
    await waitFor(() =>
      expect(screen.getByText(/no payment history yet/i)).toBeInTheDocument(),
    );
  });

  it("shows an error state when the history fetch fails", async () => {
    mockInstancesFetch([], false);
    renderWithToast(
      <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
    );
    await userEvent.click(screen.getByText(/payment history/i));
    await waitFor(() =>
      expect(screen.getByText(/could not load payment history/i)).toBeInTheDocument(),
    );
  });
});
