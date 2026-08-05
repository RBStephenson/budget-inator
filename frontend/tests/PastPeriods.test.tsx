import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PastPeriods } from "../src/components/PastPeriods";
import { ToastProvider } from "../src/context/ToastContext";
import { makePeriod, makeSchedule } from "./fixtures";

// PastPeriods renders PeriodCard -> BillRow, which calls useToast().
function renderWithToast(ui: React.ReactElement) {
  return render(<ToastProvider>{ui}</ToastProvider>);
}

function mockFetch(data: unknown, ok = true) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Internal Server Error",
    json: async () => data,
  } as Response);
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("PastPeriods", () => {
  it("renders collapsed by default and fetches nothing", () => {
    const spy = mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<PastPeriods currentStart="2025-01-17" />);
    expect(screen.getByRole("button", { name: /past periods/i })).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });

  it("fetches and shows past periods when expanded", async () => {
    mockFetch(
      makeSchedule([
        makePeriod({ period_index: 0, period_start: "2025-01-03", period_end: "2025-01-16" }),
      ]),
    );
    renderWithToast(<PastPeriods currentStart="2025-01-17" />);
    await userEvent.click(screen.getByRole("button", { name: /past periods/i }));
    await waitFor(() => expect(screen.getByText("Past")).toBeInTheDocument());
  });

  it("requests the window immediately before the current period start", async () => {
    const spy = mockFetch(makeSchedule([makePeriod()]));
    renderWithToast(<PastPeriods currentStart="2025-02-14" />);
    await userEvent.click(screen.getByRole("button", { name: /past periods/i }));
    await waitFor(() => expect(spy).toHaveBeenCalled());
    const url = String(spy.mock.calls[0][0]);
    // to = day before current start; from = 32 days earlier
    expect(url).toContain("to=2025-02-13");
    expect(url).toContain("from=2025-01-12");
  });

  it("shows an empty state when there are no past periods", async () => {
    mockFetch(makeSchedule([]));
    renderWithToast(<PastPeriods currentStart="2025-01-17" />);
    await userEvent.click(screen.getByRole("button", { name: /past periods/i }));
    await waitFor(() =>
      expect(screen.getByText(/no past periods yet/i)).toBeInTheDocument(),
    );
  });

  it("shows an error state when the fetch fails", async () => {
    mockFetch({}, false);
    renderWithToast(<PastPeriods currentStart="2025-01-17" />);
    await userEvent.click(screen.getByRole("button", { name: /past periods/i }));
    await waitFor(() =>
      expect(screen.getByText(/could not load past periods/i)).toBeInTheDocument(),
    );
  });

  it("refetches both the past window and the current schedule when a past-period action succeeds (BI-21)", async () => {
    const fetchSpy = mockFetch(makeSchedule([makePeriod()]));
    const onRefetch = vi.fn();
    renderWithToast(<PastPeriods currentStart="2025-01-17" onRefetch={onRefetch} />);

    await userEvent.click(screen.getByRole("button", { name: /past periods/i }));
    await waitFor(() => expect(screen.getByText("Past")).toBeInTheDocument());
    const callsBeforeAction = fetchSpy.mock.calls.length;

    await userEvent.click(screen.getByRole("button", { name: /edit pay date/i }));
    const input = screen.getByLabelText(/override pay date/i);
    await userEvent.clear(input);
    await userEvent.type(input, "2025-01-02");
    await userEvent.click(screen.getByRole("button", { name: /confirm pay date/i }));

    // The current-schedule refetch (Dashboard's useSchedule) was invoked...
    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
    // ...alongside the past window's own refetch, which issues a new GET.
    await waitFor(() =>
      expect(fetchSpy.mock.calls.length).toBeGreaterThan(callsBeforeAction + 1),
    );
  });
});
