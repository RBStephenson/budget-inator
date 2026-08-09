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
        onDuplicate={vi.fn()}
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
        onDuplicate={vi.fn()}
      />,
    );
    expect(screen.getAllByText("$14,400.00").length).toBeGreaterThanOrEqual(1);
  });

  it("distinguishes explicit month-end from a fixed due day", () => {
    render(
      <BillTable
        bills={[
          makeApiBill({ id: 1, name: "Fixed", due_day: 31 }),
          makeApiBill({
            id: 2,
            name: "Month end",
            due_day: null,
            due_day_is_month_end: true,
          }),
        ]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
        onDuplicate={vi.fn()}
      />,
    );
    expect(screen.getByText("Day 31")).toBeInTheDocument();
    expect(screen.getByText("Last day")).toBeInTheDocument();
  });

  it("shows the correct annual cost for a biweekly bill", () => {
    // $100 biweekly × 26 = $2,600/year
    render(
      <BillTable
        bills={[makeApiBill({ id: 1, amount: "100.00", recurrence: "biweekly", due_day: null, due_date: "2025-01-03" })]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
        onDuplicate={vi.fn()}
      />,
    );
    expect(screen.getAllByText("$2,600.00").length).toBeGreaterThanOrEqual(1);
  });

  it("shows the footer total annual cost", () => {
    const bills = [
      makeApiBill({ id: 1, amount: "1000.00", recurrence: "monthly" }), // $12,000
      makeApiBill({ id: 2, name: "Internet", amount: "100.00", recurrence: "monthly" }), // $1,200
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()}
        onDuplicate={vi.fn()} />);
    expect(screen.getByText("$13,200.00")).toBeInTheDocument();
  });

  it("calls onEdit with the correct bill", async () => {
    const onEdit = vi.fn();
    const bill = makeApiBill({ name: "Rent" });
    render(<BillTable bills={[bill]} onEdit={onEdit} onDeactivate={vi.fn()}
        onDuplicate={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /edit rent/i }));
    expect(onEdit).toHaveBeenCalledWith(bill);
  });

  it("calls onDuplicate with the correct bill", async () => {
    const onDuplicate = vi.fn();
    const bill = makeApiBill({ name: "Rent" });
    render(
      <BillTable bills={[bill]} onEdit={vi.fn()} onDeactivate={vi.fn()} onDuplicate={onDuplicate} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /duplicate rent/i }));
    expect(onDuplicate).toHaveBeenCalledWith(bill);
  });

  it("calls onDeactivate with the correct bill", async () => {
    const onDeactivate = vi.fn();
    const bill = makeApiBill({ name: "Rent" });
    render(<BillTable bills={[bill]} onEdit={vi.fn()} onDeactivate={onDeactivate} onDuplicate={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /deactivate rent/i }));
    expect(onDeactivate).toHaveBeenCalledWith(bill);
  });

  it("shows 'est.' label for variable bills", () => {
    render(
      <BillTable
        bills={[makeApiBill({ is_variable: true })]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
        onDuplicate={vi.fn()}
      />,
    );
    expect(screen.getByText("est.")).toBeInTheDocument();
  });

  it("does not show inactive bills in the main table", () => {
    const bills = [
      makeApiBill({ id: 1, name: "Active Bill", is_active: true }),
      makeApiBill({ id: 2, name: "Inactive Bill", is_active: false }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()}
        onDuplicate={vi.fn()} />);
    expect(screen.getByText("Active Bill")).toBeInTheDocument();
    // Inactive bill is hidden behind the toggle — should not be visible yet
    expect(screen.queryByText("Inactive Bill")).not.toBeInTheDocument();
  });

  it("shows inactive bills when the toggle is clicked", async () => {
    const bills = [
      makeApiBill({ id: 1, name: "Active", is_active: true }),
      makeApiBill({ id: 2, name: "Inactive", is_active: false }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()}
        onDuplicate={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /inactive bills/i }));
    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });

  // ── Search ────────────────────────────────────────────────────────────────

  it("filters bills by name when typing in the search box", async () => {
    const bills = [
      makeApiBill({ id: 1, name: "Rent" }),
      makeApiBill({ id: 2, name: "Netflix" }),
      makeApiBill({ id: 3, name: "Internet" }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()}
        onDuplicate={vi.fn()} />);
    await userEvent.type(screen.getByRole("searchbox", { name: /search bills/i }), "net");
    expect(screen.getByText("Netflix")).toBeInTheDocument();
    expect(screen.getByText("Internet")).toBeInTheDocument();
    expect(screen.queryByText("Rent")).not.toBeInTheDocument();
  });

  it("search is case-insensitive", async () => {
    render(
      <BillTable
        bills={[makeApiBill({ name: "Rent" })]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
        onDuplicate={vi.fn()}
      />,
    );
    await userEvent.type(screen.getByRole("searchbox", { name: /search bills/i }), "RENT");
    expect(screen.getByText("Rent")).toBeInTheDocument();
  });

  it("shows an empty-state message when no bills match the search", async () => {
    render(
      <BillTable
        bills={[makeApiBill({ name: "Rent" })]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
        onDuplicate={vi.fn()}
      />,
    );
    await userEvent.type(screen.getByRole("searchbox", { name: /search bills/i }), "zzz");
    expect(screen.getByText(/no bills match/i)).toBeInTheDocument();
  });

  // ── Category filter ────────────────────────────────────────────────────────

  it("filters bills by category", async () => {
    const bills = [
      makeApiBill({ id: 1, name: "Rent", category: "housing" }),
      makeApiBill({ id: 2, name: "Netflix", category: "subscriptions" }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()}
        onDuplicate={vi.fn()} />);
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: /filter by category/i }),
      "housing",
    );
    expect(screen.getByText("Rent")).toBeInTheDocument();
    expect(screen.queryByText("Netflix")).not.toBeInTheDocument();
  });

  it("composes search and category filter", async () => {
    const bills = [
      makeApiBill({ id: 1, name: "Rent", category: "housing" }),
      makeApiBill({ id: 2, name: "Rental storage", category: "other" }),
      makeApiBill({ id: 3, name: "Netflix", category: "subscriptions" }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()}
        onDuplicate={vi.fn()} />);
    await userEvent.type(screen.getByRole("searchbox", { name: /search bills/i }), "rent");
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: /filter by category/i }),
      "housing",
    );
    expect(screen.getByText("Rent")).toBeInTheDocument();
    expect(screen.queryByText("Rental storage")).not.toBeInTheDocument();
    expect(screen.queryByText("Netflix")).not.toBeInTheDocument();
  });

  it("shows a Clear filters button when a filter is active and removes it on click", async () => {
    render(
      <BillTable
        bills={[makeApiBill({ name: "Rent" })]}
        onEdit={vi.fn()}
        onDeactivate={vi.fn()}
        onDuplicate={vi.fn()}
      />,
    );
    const searchBox = screen.getByRole("searchbox", { name: /search bills/i });
    await userEvent.type(searchBox, "r");
    expect(screen.getByRole("button", { name: /clear filters/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /clear filters/i }));
    expect(screen.queryByRole("button", { name: /clear filters/i })).not.toBeInTheDocument();
    expect(searchBox).toHaveValue("");
  });

  it("footer shows filtered bill count and total when a filter is active", async () => {
    const bills = [
      makeApiBill({ id: 1, name: "Rent", amount: "1000.00", recurrence: "monthly", category: "housing" }),
      makeApiBill({ id: 2, name: "Netflix", amount: "20.00", recurrence: "monthly", category: "subscriptions" }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()}
        onDuplicate={vi.fn()} />);
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: /filter by category/i }),
      "housing",
    );
    expect(screen.getByText(/1 bill.*filtered/i)).toBeInTheDocument();
    // $12,000.00 appears in both the Rent row and the footer total
    expect(screen.getAllByText("$12,000.00")).toHaveLength(2);
    expect(screen.queryByText("$240.00")).not.toBeInTheDocument();
  });

  // ── Sort (existing, kept for completeness) ────────────────────────────────

  it("sorts by annual cost when that sort is selected", async () => {
    const bills = [
      makeApiBill({ id: 1, name: "Cheap", amount: "10.00", recurrence: "monthly" }),
      makeApiBill({ id: 2, name: "Expensive", amount: "500.00", recurrence: "monthly" }),
    ];
    render(<BillTable bills={bills} onEdit={vi.fn()} onDeactivate={vi.fn()}
        onDuplicate={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /annual cost/i }));
    const rows = screen.getAllByRole("row");
    // First data row (index 1, skipping header) should be Expensive
    expect(rows[1]).toHaveTextContent("Expensive");
  });
});
