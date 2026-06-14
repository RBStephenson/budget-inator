import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Dashboard } from "../src/components/Dashboard";
import { ToastContainer } from "../src/components/ToastContainer";
import { ToastProvider } from "../src/context/ToastContext";
import { makeBill, makeApiBill, makePeriod, makeSchedule, makeMonthlySummary } from "./fixtures";

function renderWithToast(ui: React.ReactElement) {
  return render(
    <ToastProvider>
      {ui}
      <ToastContainer />
    </ToastProvider>,
  );
}

function mockFetch(data: unknown, ok = true) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Internal Server Error",
    json: async () => data,
  } as Response);
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("Dashboard", () => {
  it("shows a loading state initially", () => {
    // Never resolves — keeps component in loading state
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    renderWithToast(<Dashboard />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows an error state when the API fails", async () => {
    mockFetch({}, false);
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText(/could not load schedule/i)).toBeInTheDocument(),
    );
  });

  it("shows onboarding CTA when no schedule is configured (404)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({}),
    } as Response);
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText(/welcome to budget-inator/i)).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: /set up pay schedule/i })).toBeInTheDocument();
  });

  it("shows an empty state when there are no periods", async () => {
    mockFetch(makeSchedule([]));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText(/no pay periods found/i)).toBeInTheDocument(),
    );
  });

  it("renders the current period hero card", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText("Current period")).toBeInTheDocument(),
    );
  });

  it("renders upcoming periods below the hero", async () => {
    const periods = [
      makePeriod({ period_index: 0 }),
      makePeriod({ period_index: 1, period_start: "2025-01-17", period_end: "2025-01-30" }),
      makePeriod({ period_index: 2, period_start: "2025-01-31", period_end: "2025-02-13" }),
    ];
    mockFetch(makeSchedule(periods));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText("Upcoming periods")).toBeInTheDocument(),
    );
    // Two upcoming cards
    expect(screen.getAllByText("Upcoming")).toHaveLength(2);
  });

  it("does not render the upcoming section when there is only one period", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText("Current period")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Upcoming periods")).not.toBeInTheDocument();
  });

  it("renders the flagged bills banner when summary has flagged bills", async () => {
    const period = makePeriod({
      flagged_bill_count: 1,
      assigned_bills: [makeBill({ status: "late_flagged", name: "Old Bill" })],
    });
    const schedule = makeSchedule([period]);
    mockFetch(schedule);
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument(),
    );
  });

  it("does not render the flagged bills banner when there are no flagged bills", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText("Current period")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders the Add Bill action button", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("link", { name: /add bill/i })).toBeInTheDocument(),
    );
  });

  it("renders the actions row above the period cards", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText("Current period")).toBeInTheDocument(),
    );
    const addBill = screen.getByRole("link", { name: /add bill/i });
    const hero = screen.getByText("Current period");
    // Add Bill must precede the hero card in document order
    expect(
      addBill.compareDocumentPosition(hero) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("renders the Annual Cost button", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /annual cost/i })).toBeInTheDocument(),
    );
  });

  it("opens the Annual Cost modal when the button is clicked", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      if (u.includes("/bills")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          statusText: "OK",
          json: async () => [],
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => makeSchedule([makePeriod()]),
      } as Response);
    });
    renderWithToast(<Dashboard />);
    await waitFor(() => screen.getByRole("button", { name: /annual cost/i }));
    await user.click(screen.getByRole("button", { name: /annual cost/i }));
    await waitFor(() =>
      expect(screen.getByText("Annual Cost Breakdown")).toBeInTheDocument(),
    );
  });

  it("shows the view toggle buttons", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /by pay period/i })).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: /by month/i })).toBeInTheDocument();
  });

  it("renders the Past periods toggle (#69)", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /past periods/i })).toBeInTheDocument(),
    );
  });
});

describe("Dashboard — monthly view toggle", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  function mockBothEndpoints(monthlyData = { months: [makeMonthlySummary()] }) {
    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      const data = u.includes("monthly-summary")
        ? monthlyData
        : makeSchedule([makePeriod()]);
      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => data,
      } as Response);
    });
  }

  it("switches to monthly view when 'By Month' is clicked", async () => {
    const user = userEvent.setup();
    mockBothEndpoints();
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /by month/i })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /by month/i }));
    await waitFor(() =>
      expect(screen.getByText(/january 2025/i)).toBeInTheDocument(),
    );
  });

  it("hides pay-period cards when monthly view is active", async () => {
    const user = userEvent.setup();
    mockBothEndpoints();
    renderWithToast(<Dashboard />);
    await waitFor(() => screen.getByText("Current period"));
    await user.click(screen.getByRole("button", { name: /by month/i }));
    await waitFor(() => screen.getByText(/january 2025/i));
    expect(screen.queryByText("Current period")).not.toBeInTheDocument();
  });

  it("switches back to pay-period view when 'By Pay Period' is clicked", async () => {
    const user = userEvent.setup();
    mockBothEndpoints();
    renderWithToast(<Dashboard />);
    await waitFor(() => screen.getByText("Current period"));
    await user.click(screen.getByRole("button", { name: /by month/i }));
    await waitFor(() => screen.getByText(/january 2025/i));
    await user.click(screen.getByRole("button", { name: /by pay period/i }));
    await waitFor(() =>
      expect(screen.getByText("Current period")).toBeInTheDocument(),
    );
  });
});

describe("Dashboard — edit bill modal", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  function mockScheduleWithBillAndGetById() {
    const assignedBill = makeBill({ bill_id: 1, name: "Rent" });
    const period = makePeriod({ assigned_bills: [assignedBill] });
    const apiBill = makeApiBill({ id: 1, name: "Rent" });

    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      if (u.match(/\/bills\/\d+$/)) {
        return Promise.resolve({
          ok: true, status: 200, statusText: "OK",
          json: async () => apiBill,
        } as Response);
      }
      return Promise.resolve({
        ok: true, status: 200, statusText: "OK",
        json: async () => makeSchedule([period]),
      } as Response);
    });

    return { period, apiBill };
  }

  it("opens the edit modal when Edit bill is clicked on a BillRow", async () => {
    const user = userEvent.setup();
    mockScheduleWithBillAndGetById();
    renderWithToast(<Dashboard />);
    // Hero card is expanded by default, so bill rows render without clicking
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /edit bill rent/i })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /edit bill rent/i }));
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Edit bill" })).toBeInTheDocument(),
    );
  });

  it("closes the edit modal when onClose is triggered", async () => {
    const user = userEvent.setup();
    mockScheduleWithBillAndGetById();
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /edit bill rent/i })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /edit bill rent/i }));
    await waitFor(() => screen.getByRole("heading", { name: "Edit bill" }));
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("heading", { name: "Edit bill" })).not.toBeInTheDocument();
  });

  it("shows an error toast when the bill fetch fails", async () => {
    const user = userEvent.setup();
    const assignedBill = makeBill({ bill_id: 1, name: "Rent" });
    const period = makePeriod({ assigned_bills: [assignedBill] });

    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      if (u.match(/\/bills\/\d+$/)) {
        return Promise.resolve({
          ok: false, status: 500, statusText: "Server Error",
          json: async () => ({}),
        } as Response);
      }
      return Promise.resolve({
        ok: true, status: 200, statusText: "OK",
        json: async () => makeSchedule([period]),
      } as Response);
    });

    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /edit bill rent/i })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /edit bill rent/i }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/could not load bill details/i),
    );
    expect(screen.queryByRole("heading", { name: "Edit bill" })).not.toBeInTheDocument();
  });
});

describe("Dashboard — PDF download", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.URL.createObjectURL = vi.fn(() => "blob:mock");
    globalThis.URL.revokeObjectURL = vi.fn();
  });
  afterEach(() => vi.restoreAllMocks());

  function mockScheduleAnd(pdf: () => Promise<Response>) {
    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      if (u.includes("budget.pdf")) return pdf();
      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => makeSchedule([makePeriod()]),
      } as Response);
    });
  }

  function pdfOk(): Promise<Response> {
    return Promise.resolve({
      ok: true,
      status: 200,
      statusText: "OK",
      blob: async () => new Blob(["%PDF-1.7"], { type: "application/pdf" }),
      headers: new Headers({
        "content-disposition": 'attachment; filename="budget-2025-01-03.pdf"',
      }),
    } as Response);
  }

  it("renders the Download PDF button", async () => {
    mockScheduleAnd(pdfOk);
    renderWithToast(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /download pdf/i })).toBeInTheDocument(),
    );
  });

  it("triggers a download when clicked", async () => {
    const user = userEvent.setup();
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    mockScheduleAnd(pdfOk);
    renderWithToast(<Dashboard />);
    await waitFor(() => screen.getByRole("button", { name: /download pdf/i }));
    await user.click(screen.getByRole("button", { name: /download pdf/i }));
    await waitFor(() => expect(clickSpy).toHaveBeenCalledOnce());
  });

  it("shows an error message when PDF generation fails", async () => {
    const user = userEvent.setup();
    mockScheduleAnd(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: "Server Error",
        blob: async () => new Blob([]),
        headers: new Headers(),
      } as Response),
    );
    renderWithToast(<Dashboard />);
    await waitFor(() => screen.getByRole("button", { name: /download pdf/i }));
    await user.click(screen.getByRole("button", { name: /download pdf/i }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/could not generate/i),
    );
  });
});
