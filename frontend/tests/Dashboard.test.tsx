import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Dashboard } from "../src/components/Dashboard";
import { makeBill, makePeriod, makeSchedule } from "./fixtures";

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
    render(<Dashboard />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows an error state when the API fails", async () => {
    mockFetch({}, false);
    render(<Dashboard />);
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
    render(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText(/welcome to budget-inator/i)).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: /set up pay schedule/i })).toBeInTheDocument();
  });

  it("shows an empty state when there are no periods", async () => {
    mockFetch(makeSchedule([]));
    render(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText(/no pay periods found/i)).toBeInTheDocument(),
    );
  });

  it("renders the current period hero card", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    render(<Dashboard />);
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
    render(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText("Upcoming periods")).toBeInTheDocument(),
    );
    // Two upcoming cards
    expect(screen.getAllByText("Upcoming")).toHaveLength(2);
  });

  it("does not render the upcoming section when there is only one period", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    render(<Dashboard />);
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
    render(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument(),
    );
  });

  it("does not render the flagged bills banner when there are no flagged bills", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    render(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByText("Current period")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders the Add Bill action button", async () => {
    mockFetch(makeSchedule([makePeriod()]));
    render(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByRole("link", { name: /add bill/i })).toBeInTheDocument(),
    );
  });
});
