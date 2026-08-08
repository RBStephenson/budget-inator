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

  it("shows the next payday stat once schedule data loads", async () => {
    renderSidebar("dashboard");
    expect(await screen.findByText(/next payday/i)).toBeInTheDocument();
    expect(await screen.findByText(/jul 24/i)).toBeInTheDocument();
  });
});

describe("Sidebar - flagged bill badge", () => {
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
