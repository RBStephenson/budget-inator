import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Dashboard } from "../src/components/Dashboard";
import { Sidebar } from "../src/components/Sidebar";
import { ToastContainer } from "../src/components/ToastContainer";
import { ScheduleProvider } from "../src/context/ScheduleContext";
import { ToastProvider } from "../src/context/ToastContext";
import { makePeriod, makeSchedule } from "./fixtures";

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("ScheduleContext — Sidebar/Dashboard consistency (BI-22)", () => {
  it("reflects a payday change made in the Dashboard in the Sidebar without a reload", async () => {
    const user = userEvent.setup();

    // First fetch (initial mount): pay_date Aug 15. Second fetch (after the
    // Dashboard's PeriodCard override-refetch): pay_date Aug 17.
    let call = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      if (u.includes("/bills")) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response);
      }
      call += 1;
      const payDate = call === 1 ? "2026-08-15" : "2026-08-17";
      const period = makePeriod({ pay_date: payDate, original_pay_date: payDate });
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => makeSchedule([period]),
      } as Response);
    });

    render(
      <ToastProvider>
        <ScheduleProvider>
          <Sidebar page="dashboard" />
          <Dashboard />
        </ScheduleProvider>
        <ToastContainer />
      </ToastProvider>,
    );

    await waitFor(() => expect(screen.getByText("Current period")).toBeInTheDocument());
    const sidebarPayday = () => document.querySelector(".sidebar__stat-value");
    expect(sidebarPayday()).toHaveTextContent(/aug 15/i);

    // Simulate the effect of PeriodCard's payday override: Dashboard calls
    // its shared refetch(), which must also update the Sidebar's copy.
    const quickAddInput = screen.getByLabelText(/bill name/i);
    await user.type(quickAddInput, "Gym");
    await user.type(screen.getByLabelText(/amount/i), "40");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() => expect(sidebarPayday()).toHaveTextContent(/aug 17/i));
  });
});
