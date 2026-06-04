import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { PeriodCard } from "../src/components/PeriodCard";
import { makeBill, makePeriod } from "./fixtures";

describe("PeriodCard", () => {
  it("renders the period date range", () => {
    render(<PeriodCard period={makePeriod()} />);
    expect(screen.getByText(/Jan 3/)).toBeInTheDocument();
    expect(screen.getByText(/Jan 16/)).toBeInTheDocument();
  });

  it("shows 'Current period' label when isHero=true", () => {
    render(<PeriodCard period={makePeriod()} isHero />);
    expect(screen.getByText("Current period")).toBeInTheDocument();
  });

  it("shows 'Upcoming' label when isHero=false", () => {
    render(<PeriodCard period={makePeriod()} />);
    expect(screen.getByText("Upcoming")).toBeInTheDocument();
  });

  it("is expanded by default when isHero=true", () => {
    const period = makePeriod({ assigned_bills: [makeBill({ name: "Rent" })] });
    render(<PeriodCard period={period} isHero />);
    expect(screen.getByText("Rent")).toBeInTheDocument();
  });

  it("is collapsed by default when isHero=false", () => {
    const period = makePeriod({ assigned_bills: [makeBill({ name: "Rent" })] });
    render(<PeriodCard period={period} />);
    expect(screen.queryByText("Rent")).not.toBeInTheDocument();
  });

  it("expands on click when collapsed", async () => {
    const user = userEvent.setup();
    const period = makePeriod({ assigned_bills: [makeBill({ name: "Rent" })] });
    render(<PeriodCard period={period} />);
    await user.click(screen.getByRole("button"));
    expect(screen.getByText("Rent")).toBeInTheDocument();
  });

  it("collapses on second click", async () => {
    const user = userEvent.setup();
    const period = makePeriod({ assigned_bills: [makeBill({ name: "Rent" })] });
    render(<PeriodCard period={period} isHero />);
    const btn = screen.getByRole("button");
    await user.click(btn);
    expect(screen.queryByText("Rent")).not.toBeInTheDocument();
    await user.click(btn);
    expect(screen.getByText("Rent")).toBeInTheDocument();
  });

  it("shows 'No bills this period' when the period has no bills", () => {
    render(<PeriodCard period={makePeriod({ assigned_bills: [] })} isHero />);
    expect(screen.getByText(/no bills this period/i)).toBeInTheDocument();
  });

  it("applies the overspent class when remaining_balance is negative", () => {
    const { container } = render(
      <PeriodCard period={makePeriod({ remaining_balance: "-50.00" })} />,
    );
    expect(container.querySelector(".period-card--overspent")).toBeInTheDocument();
  });

  it("shows 'Overspent' label when remaining balance is negative", () => {
    render(<PeriodCard period={makePeriod({ remaining_balance: "-50.00" })} />);
    expect(screen.getByText("Overspent")).toBeInTheDocument();
  });

  it("shows flagged badge when period has flagged bills", () => {
    render(<PeriodCard period={makePeriod({ flagged_bill_count: 2 })} />);
    expect(screen.getByLabelText(/2 late bill/i)).toBeInTheDocument();
  });

  it("does not show flagged badge when no flagged bills", () => {
    render(<PeriodCard period={makePeriod({ flagged_bill_count: 0 })} />);
    expect(screen.queryByLabelText(/late bill/i)).not.toBeInTheDocument();
  });

  it("renders opening balance, total bills, and available figures", () => {
    render(
      <PeriodCard
        period={makePeriod({
          opening_balance: "2000.00",
          total_bills: "800.00",
          remaining_balance: "1200.00",
        })}
      />,
    );
    expect(screen.getByText("$2,000.00")).toBeInTheDocument();
    expect(screen.getByText("−$800.00")).toBeInTheDocument();
    expect(screen.getByText("$1,200.00")).toBeInTheDocument();
  });
});
