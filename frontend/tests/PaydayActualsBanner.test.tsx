import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PaydayActualsBanner } from "../src/components/PaydayActualsBanner";
import { ToastContainer } from "../src/components/ToastContainer";
import { ToastProvider } from "../src/context/ToastContext";
import { makePeriod } from "./fixtures";

function renderWithToast(ui: React.ReactElement) {
  return render(
    <ToastProvider>
      {ui}
      <ToastContainer />
    </ToastProvider>,
  );
}

interface ActualRow {
  pay_date: string;
  actual_net_pay: string | null;
  actual_balance: string | null;
}

function mockApi({ actuals = [] as ActualRow[], putOk = true } = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((url, init) => {
    const u = String(url);
    if (u.includes("/pay-period-actuals")) {
      if ((init as RequestInit | undefined)?.method === "PUT") {
        return Promise.resolve({
          ok: putOk,
          status: putOk ? 200 : 500,
          statusText: putOk ? "OK" : "Server Error",
          json: async () => ({}),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => actuals,
      } as Response);
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({}),
    } as Response);
  });
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("PaydayActualsBanner", () => {
  it("shows the banner when the payday has no recorded actuals", async () => {
    mockApi({ actuals: [] });
    renderWithToast(
      <PaydayActualsBanner
        period={makePeriod({ original_pay_date: "2025-01-03" })}
        onRecorded={vi.fn()}
      />,
    );
    await waitFor(() =>
      expect(screen.getByText(/confirm your deposit and balance/i)).toBeInTheDocument(),
    );
  });

  it("does not show when actuals are already recorded", async () => {
    const spy = mockApi({
      actuals: [{ pay_date: "2025-01-03", actual_net_pay: null, actual_balance: "100.00" }],
    });
    renderWithToast(
      <PaydayActualsBanner
        period={makePeriod({ original_pay_date: "2025-01-03" })}
        onRecorded={vi.fn()}
      />,
    );
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(screen.queryByText(/confirm your deposit and balance/i)).not.toBeInTheDocument();
  });

  it("does not show when the payday is in the future", async () => {
    const spy = mockApi({ actuals: [] });
    renderWithToast(
      <PaydayActualsBanner
        period={makePeriod({ original_pay_date: "2999-01-01" })}
        onRecorded={vi.fn()}
      />,
    );
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(screen.queryByText(/confirm your deposit and balance/i)).not.toBeInTheDocument();
  });

  it("submits the entered balance and re-anchors via onRecorded", async () => {
    const onRecorded = vi.fn();
    const spy = mockApi({ actuals: [] });
    renderWithToast(
      <PaydayActualsBanner
        period={makePeriod({ original_pay_date: "2025-01-03" })}
        onRecorded={onRecorded}
      />,
    );
    await waitFor(() => screen.getByRole("button", { name: /^confirm$/i }));
    await userEvent.click(screen.getByRole("button", { name: /^confirm$/i }));
    await userEvent.type(screen.getByLabelText(/current balance/i), "3450.00");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(onRecorded).toHaveBeenCalledOnce());
    const putCall = spy.mock.calls.find(
      (c) => (c[1] as RequestInit | undefined)?.method === "PUT",
    );
    expect(putCall).toBeDefined();
    const body = JSON.parse((putCall![1] as RequestInit).body as string);
    expect(parseFloat(body.actual_balance)).toBeCloseTo(3450);
    expect(body.actual_net_pay).toBeUndefined();
    expect(String(putCall![0])).toContain("/pay-period-actuals/2025-01-03");
  });

  it("keeps the Save button disabled until a field is entered", async () => {
    mockApi({ actuals: [] });
    renderWithToast(
      <PaydayActualsBanner
        period={makePeriod({ original_pay_date: "2025-01-03" })}
        onRecorded={vi.fn()}
      />,
    );
    await waitFor(() => screen.getByRole("button", { name: /^confirm$/i }));
    await userEvent.click(screen.getByRole("button", { name: /^confirm$/i }));
    expect(screen.getByRole("button", { name: /^save$/i })).toBeDisabled();
  });
});
