import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { BillRow } from "../src/components/BillRow";
import { makeBill } from "./fixtures";

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

  it("calls onRefetch after marking paid", async () => {
    mockPatch();
    const onRefetch = vi.fn();
    render(
      <BillRow bill={makeBill({ status: "on_time" })} payOnDate="2025-01-03" onRefetch={onRefetch} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /paid/i }));
    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
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
});
