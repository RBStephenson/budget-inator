import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Sidebar } from "../src/components/Sidebar";
import { ScheduleProvider } from "../src/context/ScheduleContext";

function renderSidebar(page: Parameters<typeof Sidebar>[0]["page"]) {
  return render(
    <ScheduleProvider>
      <Sidebar page={page} />
    </ScheduleProvider>,
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      periods: [{ pay_date: "2026-07-24" }],
      summary: { from_date: "", to_date: "", period_count: 1, total_flagged_bills: 0 },
    }),
  } as Response);
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("Sidebar", () => {
  it("renders all four nav links", () => {
    renderSidebar("dashboard");
    expect(screen.getByRole("link", { name: /dashboard/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /bills/i })).toHaveAttribute("href", "/bills");
    expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: /^help$/i })).toHaveAttribute("href", "/help");
  });

  it("marks the current page's link as active", () => {
    renderSidebar("bills");
    expect(screen.getByRole("link", { name: /bills/i })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /dashboard/i })).not.toHaveAttribute("aria-current");
  });

  it("toggles dark mode and persists the preference", async () => {
    const user = userEvent.setup();
    renderSidebar("dashboard");

    const toggle = screen.getByRole("button", { name: /dark mode/i });
    await user.click(toggle);

    expect(localStorage.getItem("budgetinator-dark")).toBe("1");
    expect(await screen.findByRole("button", { name: /light mode/i })).toBeInTheDocument();
  });

});

// The schedule's first period is the one *containing* today, so its payday is
// usually in the past. "Next payday" must be the first pay_date on or after
// today (BI-64). Only Date is faked, so findBy* polling still runs on real timers.
describe("Sidebar - next payday", () => {
  function mockPeriods(payDates: string[], totalFlaggedBills = 0) {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        periods: payDates.map((pay_date) => ({ pay_date })),
        summary: {
          from_date: "",
          to_date: "",
          period_count: payDates.length,
          total_flagged_bills: totalFlaggedBills,
        },
      }),
    } as Response);
  }

  function setToday(year: number, monthIndex: number, day: number) {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(year, monthIndex, day, 12, 0));
  }

  afterEach(() => vi.useRealTimers());

  it("shows the upcoming payday, not the one that already passed", async () => {
    setToday(2026, 9, 3);
    mockPeriods(["2026-10-02", "2026-10-16", "2026-10-30"]);
    renderSidebar("dashboard");

    expect(await screen.findByText(/next payday/i)).toBeInTheDocument();
    expect(screen.getByText("Oct 16")).toBeInTheDocument();
    expect(screen.queryByText("Oct 2")).not.toBeInTheDocument();
  });

  it("shows today when today is payday", async () => {
    setToday(2026, 9, 16);
    mockPeriods(["2026-10-02", "2026-10-16", "2026-10-30"]);
    renderSidebar("dashboard");

    await screen.findByText(/next payday/i);
    expect(screen.getByText("Oct 16")).toBeInTheDocument();
  });

  it("uses the effective pay_date when a payday was overridden", async () => {
    // The 10-16 payday was moved to 10-14 by an override; pay_date carries
    // the effective date, so that is what the Sidebar must show.
    setToday(2026, 9, 3);
    mockPeriods(["2026-10-02", "2026-10-14", "2026-10-30"]);
    renderSidebar("dashboard");

    await screen.findByText(/next payday/i);
    expect(screen.getByText("Oct 14")).toBeInTheDocument();
  });

  it("hides the stat when no loaded payday is today or later", async () => {
    setToday(2026, 9, 3);
    // A flagged bill gives a positive anchor: its badge renders only once the
    // schedule data has landed, so the absence check can't pass vacuously
    // against a still-loading sidebar.
    mockPeriods(["2026-09-18", "2026-10-02"], 1);
    renderSidebar("dashboard");

    await screen.findByLabelText(/1 bill cannot be paid on time/i);
    expect(screen.queryByText(/next payday/i)).not.toBeInTheDocument();
  });
});

describe("Sidebar - flagged bill badge", () => {
  // Some of these anchor on the "Next payday" stat, which only shows a payday
  // on or after today (BI-64): pin the clock before the mocked Jul 24 payday.
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 6, 20, 12, 0));
  });
  afterEach(() => vi.useRealTimers());

  function mockFlagged(totalFlaggedBills: number) {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        periods: [{ pay_date: "2026-07-24" }],
        summary: {
          from_date: "",
          to_date: "",
          period_count: 1,
          total_flagged_bills: totalFlaggedBills,
        },
      }),
    } as Response);
  }

  it("shows no badge when there are no flagged bills", async () => {
    mockFlagged(0);
    renderSidebar("dashboard");
    await screen.findByText(/next payday/i);
    expect(screen.queryByLabelText(/cannot be paid on time/i)).not.toBeInTheDocument();
  });

  it("shows a badge with the flagged count on the Dashboard link", async () => {
    mockFlagged(3);
    renderSidebar("dashboard");
    const badge = await screen.findByLabelText(/3 bills cannot be paid on time/i);
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toBe("3");
  });

  it("uses singular wording for a count of 1", async () => {
    mockFlagged(1);
    renderSidebar("dashboard");
    expect(await screen.findByLabelText(/1 bill cannot be paid on time/i)).toBeInTheDocument();
  });

  it("does not show a badge on the other nav links", async () => {
    mockFlagged(2);
    renderSidebar("dashboard");
    await screen.findByLabelText(/2 bills cannot be paid on time/i);
    const billsLink = screen.getByRole("link", { name: /^bills$/i });
    expect(billsLink.querySelector(".sidebar__nav-badge")).not.toBeInTheDocument();
  });
});
