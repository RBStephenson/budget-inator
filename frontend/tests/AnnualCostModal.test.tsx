import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AnnualCostModal } from "../src/components/AnnualCostModal";
import { makeApiBill } from "./fixtures";

function mockBills(bills: ReturnType<typeof makeApiBill>[], ok = true) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Internal Server Error",
    json: async () => bills,
  } as Response);
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("AnnualCostModal", () => {
  it("shows a loading state before bills arrive", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    render(<AnnualCostModal onClose={() => {}} />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows an error state when the API fails", async () => {
    mockBills([], false);
    render(<AnnualCostModal onClose={() => {}} />);
    await waitFor(() =>
      expect(screen.getByText(/could not load bills/i)).toBeInTheDocument(),
    );
  });

  it("shows an empty state when there are no active bills", async () => {
    mockBills([]);
    render(<AnnualCostModal onClose={() => {}} />);
    await waitFor(() =>
      expect(screen.getByText(/no active bills/i)).toBeInTheDocument(),
    );
  });

  it("filters out inactive bills", async () => {
    mockBills([
      makeApiBill({ id: 1, name: "Active Bill", is_active: true }),
      makeApiBill({ id: 2, name: "Deleted Bill", is_active: false }),
    ]);
    render(<AnnualCostModal onClose={() => {}} />);
    await waitFor(() => screen.getByText("Active Bill"));
    expect(screen.queryByText("Deleted Bill")).not.toBeInTheDocument();
  });

  it("renders the modal title", async () => {
    mockBills([makeApiBill()]);
    render(<AnnualCostModal onClose={() => {}} />);
    await waitFor(() =>
      expect(screen.getByText("Annual Cost Breakdown")).toBeInTheDocument(),
    );
  });

  it("shows bill name and annual cost", async () => {
    mockBills([makeApiBill({ name: "Rent", amount: "1200.00", recurrence: "monthly" })]);
    render(<AnnualCostModal onClose={() => {}} />);
    await waitFor(() => screen.getByText("Rent"));
    // monthly $1200 × 12 = $14,400/yr
    expect(screen.getByText("$14,400.00")).toBeInTheDocument();
  });

  it("shows the tilde prefix on per-payment amount for variable bills", async () => {
    mockBills([
      makeApiBill({ name: "Electric", amount: "80.00", recurrence: "monthly", is_variable: true }),
    ]);
    render(<AnnualCostModal onClose={() => {}} />);
    await waitFor(() => screen.getByText("Electric"));
    expect(screen.getByText("~$80.00")).toBeInTheDocument();
  });

  it("groups bills under their category heading", async () => {
    mockBills([
      makeApiBill({ id: 1, name: "Rent", category: "housing" }),
      makeApiBill({ id: 2, name: "Netflix", category: "subscriptions" }),
    ]);
    render(<AnnualCostModal onClose={() => {}} />);
    await waitFor(() => screen.getByText("Housing"));
    expect(screen.getByText("Subscriptions")).toBeInTheDocument();
  });

  it("shows the grand total annual cost", async () => {
    mockBills([
      makeApiBill({ id: 1, name: "Rent", amount: "1000.00", recurrence: "monthly", category: "housing" }),
      makeApiBill({ id: 2, name: "Netflix", amount: "20.00", recurrence: "monthly", category: "subscriptions" }),
    ]);
    render(<AnnualCostModal onClose={() => {}} />);
    await waitFor(() => screen.getByText("Total annual cost"));
    // $1000×12 + $20×12 = $12,240
    expect(screen.getByText("$12,240.00")).toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    mockBills([makeApiBill()]);
    render(<AnnualCostModal onClose={onClose} />);
    await waitFor(() => screen.getByText("Annual Cost Breakdown"));
    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when clicking the backdrop", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    mockBills([makeApiBill()]);
    render(<AnnualCostModal onClose={onClose} />);
    await waitFor(() => screen.getByText("Annual Cost Breakdown"));
    await user.click(screen.getByRole("dialog"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
