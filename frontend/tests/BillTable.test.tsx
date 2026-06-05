import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { BillTable } from "../src/components/BillTable";
import { makeApiBill } from "./fixtures";

describe("BillTable", () => {
  it("renders bill names", () => {
    render(
      <BillTable
        bills={[makeApiBill({ name: "Rent" }), makeApiBill({ id: 2, name: "Electric" })]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
      />,
    );
    expect(screen.getByText("Rent")).toBeInTheDocument();
    expect(screen.getByText("Electric")).toBeInTheDocument();
  });

  it("shows the correct annual cost for a monthly bill", () => {
    // $1200/month × 12 = $14,400/year — appears in row and footer
    render(
      <BillTable
        bills={[makeApiBill({ amount: "1200.00", recurrence: "monthly" })]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
      />,
    );
    expect(screen.getAllByText("$14,400.00").length).toBeGreaterThanOrEqual(1);
  });

  it("shows the correct annual cost for a biweekly bill", () => {
    // $100 biweekly × 26 = $2,600/year
    render(
      <BillTable
        bills={[makeApiBill({ id: 1, amount: "100.00", recurrence: "biweekly", due_day: null, due_date: "2025-01-03" })]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
      />,
    );
    expect(screen.getAllByText("$2,600.00").length).toBeGreaterThanOrEqual(1);
  });

  it("shows the footer total annual cost", () => {
    const bills = [
      makeApiBill({ id: 1, amount: "1000.00", recurrence: "monthly" }), // $12,000
      makeApiBill({ id: 2, name: "Internet", amount: "100.00", recurrence: "monthly" }), // $1,200
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()} />);
    expect(screen.getByText("$13,200.00")).toBeInTheDocument();
  });

  it("calls onEdit with the correct bill", async () => {
    const onEdit = vi.fn();
    const bill = makeApiBill({ name: "Rent" });
    render(<BillTable bills={[bill]} onEdit={onEdit} onDeactivate={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /edit rent/i }));
    expect(onEdit).toHaveBeenCalledWith(bill);
  });

  it("calls onDeactivate with the correct bill", async () => {
    const onDeactivate = vi.fn();
    const bill = makeApiBill({ name: "Rent" });
    render(<BillTable bills={[bill]} onEdit={vi.fn()} onDeactivate={onDeactivate} />);
    await userEvent.click(screen.getByRole("button", { name: /deactivate rent/i }));
    expect(onDeactivate).toHaveBeenCalledWith(bill);
  });

  it("shows 'est.' label for variable bills", () => {
    render(
      <BillTable
        bills={[makeApiBill({ is_variable: true })]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
      />,
    );
    expect(screen.getByText("est.")).toBeInTheDocument();
  });

  it("does not show inactive bills in the main table", () => {
    const bills = [
      makeApiBill({ id: 1, name: "Active Bill", is_active: true }),
      makeApiBill({ id: 2, name: "Inactive Bill", is_active: false }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()} />);
    expect(screen.getByText("Active Bill")).toBeInTheDocument();
    // Inactive bill is hidden behind the toggle — should not be visible yet
    expect(screen.queryByText("Inactive Bill")).not.toBeInTheDocument();
  });

  it("shows inactive bills when the toggle is clicked", async () => {
    const bills = [
      makeApiBill({ id: 1, name: "Active", is_active: true }),
      makeApiBill({ id: 2, name: "Inactive", is_active: false }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /inactive bills/i }));
    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });

  it("sorts by annual cost when that sort is selected", async () => {
    const bills = [
      makeApiBill({ id: 1, name: "Cheap", amount: "10.00", recurrence: "monthly" }),
      makeApiBill({ id: 2, name: "Expensive", amount: "500.00", recurrence: "monthly" }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /annual cost/i }));
    const rows = screen.getAllByRole("row");
    // First data row (index 1, skipping header) should be Expensive
    expect(rows[1]).toHaveTextContent("Expensive");
  });
});
