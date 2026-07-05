import { fireEvent, render as rtlRender, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { BillRow } from "../src/components/BillRow";
import { ToastContainer } from "../src/components/ToastContainer";
import { ToastProvider } from "../src/context/ToastContext";
import { makeBill } from "./fixtures";

// BillRow calls useToast(); wrap every render in a ToastProvider with a
// ToastContainer so error toasts can be asserted.
function render(ui: React.ReactElement) {
  return rtlRender(
    <ToastProvider>
      {ui}
      <ToastContainer />
    </ToastProvider>,
  );
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

function mockPatch(ok = true) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Internal Server Error",
    json: async () => ({}),
  } as Response);
}

describe("BillRow", () => {
  it("renders the bill name", () => {
    render(<BillRow bill={makeBill({ name: "Internet" })} payOnDate="2025-01-03" />);
    expect(screen.getByText("Internet")).toBeInTheDocument();
  });

  it("renders the amount", () => {
    render(<BillRow bill={makeBill({ amount: "99.99" })} payOnDate="2025-01-03" />);
    expect(screen.getByText("$99.99")).toBeInTheDocument();
  });

  it("shows due and pay date labels", () => {
    render(<BillRow bill={makeBill({ due_date: "2025-01-15" })} payOnDate="2025-01-03" />);
    expect(screen.getByText("Due")).toBeInTheDocument();
    expect(screen.getByText("Pay")).toBeInTheDocument();
  });

  it("does not show the late badge for on_time bills", () => {
    render(<BillRow bill={makeBill({ status: "on_time" })} payOnDate="2025-01-03" />);
    expect(screen.queryByLabelText(/late/i)).not.toBeInTheDocument();
  });

  it("shows the late badge and applies late class for late_flagged bills", () => {
    const { container } = render(
      <BillRow bill={makeBill({ status: "late_flagged" })} payOnDate="2025-01-03" />,
    );
    expect(screen.getByLabelText(/late/i)).toBeInTheDocument();
    expect(container.querySelector(".bill-row--late")).toBeInTheDocument();
  });

  it("shows Paid and Skip buttons for a pending bill", () => {
    render(<BillRow bill={makeBill({ status: "on_time" })} payOnDate="2025-01-03" />);
    expect(screen.getByRole("button", { name: /paid/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /skip/i })).toBeInTheDocument();
  });

  it("shows Undo button and paid badge for a paid bill", () => {
    const { container } = render(
      <BillRow bill={makeBill({ status: "paid" })} payOnDate="2025-01-03" />,
    );
    expect(screen.getByRole("button", { name: /undo/i })).toBeInTheDocument();
    expect(container.querySelector(".bill-row--paid")).toBeInTheDocument();
  });

  it("shows Undo button and skipped styling for a skipped bill", () => {
    const { container } = render(
      <BillRow bill={makeBill({ status: "skipped" })} payOnDate="2025-01-03" />,
    );
    expect(screen.getByRole("button", { name: /undo/i })).toBeInTheDocument();
    expect(container.querySelector(".bill-row--skipped")).toBeInTheDocument();
  });

  it("displays actual_amount when present", () => {
    render(
      <BillRow
        bill={makeBill({ status: "paid", actual_amount: "75.00", amount: "100.00" })}
        payOnDate="2025-01-03"
      />,
    );
    expect(screen.getByText("$75.00")).toBeInTheDocument();
  });

  it("reveals a paid-date input when Paid is clicked", async () => {
    render(<BillRow bill={makeBill({ status: "on_time" })} payOnDate="2025-01-03" />);
    await userEvent.click(screen.getByRole("button", { name: /^paid$/i }));
    expect(screen.getByLabelText("Paid date")).toBeInTheDocument();
  });

  it("hides the paid-date input after cancel", async () => {
    render(<BillRow bill={makeBill({ status: "on_time" })} payOnDate="2025-01-03" />);
    await userEvent.click(screen.getByRole("button", { name: /^paid$/i }));
    await userEvent.click(screen.getByRole("button", { name: /cancel paid/i }));
    expect(screen.queryByLabelText("Paid date")).not.toBeInTheDocument();
  });

  it("calls onRefetch after confirming a payment", async () => {
    mockPatch();
    const onRefetch = vi.fn();
    render(
      <BillRow bill={makeBill({ status: "on_time" })} payOnDate="2025-01-03" onRefetch={onRefetch} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /^paid$/i }));
    await userEvent.click(screen.getByRole("button", { name: /confirm paid date/i }));
    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
  });

  it("sends a back-dated paid_at when the date is changed (#69)", async () => {
    mockPatch();
    render(<BillRow bill={makeBill({ status: "on_time" })} payOnDate="2025-01-03" />);
    await userEvent.click(screen.getByRole("button", { name: /^paid$/i }));
    fireEvent.change(screen.getByLabelText("Paid date"), {
      target: { value: "2025-01-02" },
    });
    await userEvent.click(screen.getByRole("button", { name: /confirm paid date/i }));
    await waitFor(() => {
      const fetchMock = vi.mocked(globalThis.fetch);
      const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
      expect(body.status).toBe("paid");
      expect(body.paid_at).toBe("2025-01-02");
    });
  });

  it("calls onRefetch after skipping", async () => {
    mockPatch();
    const onRefetch = vi.fn();
    render(
      <BillRow bill={makeBill({ status: "on_time" })} payOnDate="2025-01-03" onRefetch={onRefetch} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /skip/i }));
    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
  });

  it("calls onRefetch after undoing", async () => {
    mockPatch();
    const onRefetch = vi.fn();
    render(
      <BillRow bill={makeBill({ status: "paid" })} payOnDate="2025-01-03" onRefetch={onRefetch} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /undo/i }));
    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
  });

  it("sends manual_pay_date when confirming a bill move", async () => {
    mockPatch();
    const onRefetch = vi.fn();
    render(
      <BillRow
        bill={makeBill({ status: "on_time" })}
        payOnDate="2025-01-03"
        onRefetch={onRefetch}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /^move$/i }));
    fireEvent.change(screen.getByLabelText(/move bill to pay date/i), {
      target: { value: "2025-01-17" },
    });
    await userEvent.click(screen.getByRole("button", { name: /confirm bill move/i }));

    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
    const fetchMock = vi.mocked(globalThis.fetch);
    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(body.status).toBe("pending");
    expect(body.manual_pay_date).toBe("2025-01-17");
  });

  it("shows moved metadata and can reset a manual move", async () => {
    mockPatch();
    const onRefetch = vi.fn();
    render(
      <BillRow
        bill={makeBill({
          placement_source: "manual",
          manual_pay_date: "2025-01-17",
        })}
        payOnDate="2025-01-17"
        onRefetch={onRefetch}
      />,
    );

    expect(screen.getByText(/moved to jan 17/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /reset bill move/i }));

    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
    const fetchMock = vi.mocked(globalThis.fetch);
    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(body.manual_pay_date).toBeNull();
  });

  it("shows an error toast and skips refetch when marking paid fails", async () => {
    mockPatch(false);
    const onRefetch = vi.fn();
    render(
      <BillRow bill={makeBill({ status: "on_time" })} payOnDate="2025-01-03" onRefetch={onRefetch} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /^paid$/i }));
    await userEvent.click(screen.getByRole("button", { name: /confirm paid date/i }));
    await waitFor(() =>
      expect(
        screen.getByText(/could not update the bill status/i),
      ).toBeInTheDocument(),
    );
    expect(onRefetch).not.toHaveBeenCalled();
  });
});

describe("BillRow — variable bill", () => {
  it("shows tilde indicator for variable bill without actual amount", () => {
    render(
      <BillRow bill={makeBill({ is_variable: true, actual_amount: null })} payOnDate="2025-01-03" />,
    );
    expect(screen.getByLabelText("estimated")).toBeInTheDocument();
  });

  it("does not show tilde indicator when actual amount is set", () => {
    render(
      <BillRow
        bill={makeBill({ is_variable: true, actual_amount: "110.00" })}
        payOnDate="2025-01-03"
      />,
    );
    expect(screen.queryByLabelText("estimated")).not.toBeInTheDocument();
  });

  it("does not show tilde indicator for non-variable bills", () => {
    render(<BillRow bill={makeBill({ is_variable: false })} payOnDate="2025-01-03" />);
    expect(screen.queryByLabelText("estimated")).not.toBeInTheDocument();
  });

  it("shows Enter actual button for variable pending bills", () => {
    render(<BillRow bill={makeBill({ is_variable: true })} payOnDate="2025-01-03" />);
    expect(screen.getByRole("button", { name: /enter actual/i })).toBeInTheDocument();
  });

  it("shows Edit actual button when actual amount already set", () => {
    render(
      <BillRow
        bill={makeBill({ is_variable: true, actual_amount: "110.00" })}
        payOnDate="2025-01-03"
      />,
    );
    expect(screen.getByRole("button", { name: /edit actual amount/i })).toBeInTheDocument();
  });

  it("does not show Enter actual button for paid variable bills", () => {
    render(
      <BillRow bill={makeBill({ is_variable: true, status: "paid" })} payOnDate="2025-01-03" />,
    );
    expect(screen.queryByRole("button", { name: /enter actual/i })).not.toBeInTheDocument();
  });

  it("does not show Enter actual button for non-variable bills", () => {
    render(<BillRow bill={makeBill({ is_variable: false })} payOnDate="2025-01-03" />);
    expect(screen.queryByRole("button", { name: /enter actual/i })).not.toBeInTheDocument();
  });

  it("reveals input when Enter actual is clicked", async () => {
    render(<BillRow bill={makeBill({ is_variable: true })} payOnDate="2025-01-03" />);
    await userEvent.click(screen.getByRole("button", { name: /enter actual/i }));
    expect(screen.getByRole("spinbutton", { name: /actual amount/i })).toBeInTheDocument();
  });

  it("calls patchBillInstance with actual_amount when confirmed", async () => {
    mockPatch();
    const onRefetch = vi.fn();
    render(
      <BillRow
        bill={makeBill({ is_variable: true })}
        payOnDate="2025-01-03"
        onRefetch={onRefetch}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /enter actual/i }));
    await userEvent.type(screen.getByRole("spinbutton", { name: /actual amount/i }), "95.50");
    await userEvent.click(screen.getByRole("button", { name: /confirm actual/i }));
    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
    const fetchMock = vi.mocked(globalThis.fetch);
    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(parseFloat(body.actual_amount)).toBeCloseTo(95.5);
    expect(body.status).toBe("pending");
  });

  it("shows an error toast and keeps the editor open when saving the actual fails", async () => {
    mockPatch(false);
    render(<BillRow bill={makeBill({ is_variable: true })} payOnDate="2025-01-03" />);
    await userEvent.click(screen.getByRole("button", { name: /enter actual/i }));
    await userEvent.type(screen.getByRole("spinbutton", { name: /actual amount/i }), "95.50");
    await userEvent.click(screen.getByRole("button", { name: /confirm actual/i }));
    await waitFor(() =>
      expect(
        screen.getByText(/could not save the actual amount/i),
      ).toBeInTheDocument(),
    );
    // Editor stays open with the typed value intact
    expect(screen.getByRole("spinbutton", { name: /actual amount/i })).toHaveValue(95.5);
  });

  it("hides input after cancel", async () => {
    render(<BillRow bill={makeBill({ is_variable: true })} payOnDate="2025-01-03" />);
    await userEvent.click(screen.getByRole("button", { name: /enter actual/i }));
    expect(screen.getByRole("spinbutton", { name: /actual amount/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /cancel actual/i }));
    expect(screen.queryByRole("spinbutton", { name: /actual amount/i })).not.toBeInTheDocument();
  });
});

describe("BillRow — edit bill", () => {
  it("does not render the Edit bill button when onEdit is not provided", () => {
    render(<BillRow bill={makeBill({ name: "Rent" })} payOnDate="2025-01-03" />);
    expect(screen.queryByRole("button", { name: /edit bill/i })).not.toBeInTheDocument();
  });

  it("renders the Edit bill button when onEdit is provided", () => {
    render(
      <BillRow bill={makeBill({ name: "Rent" })} payOnDate="2025-01-03" onEdit={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: /edit bill rent/i })).toBeInTheDocument();
  });

  it("calls onEdit with the bill_id when clicked", async () => {
    const onEdit = vi.fn();
    render(
      <BillRow bill={makeBill({ bill_id: 42, name: "Rent" })} payOnDate="2025-01-03" onEdit={onEdit} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /edit bill rent/i }));
    expect(onEdit).toHaveBeenCalledWith(42);
  });
});
