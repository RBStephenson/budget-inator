import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { MonthCard } from "../src/components/MonthCard";
import {
  makeMonthlySummary,
  makeMonthlyCategoryGroup,
  makeMonthlyBillItem,
} from "./fixtures";

describe("MonthCard", () => {
  it("renders the formatted month name", () => {
    render(<MonthCard summary={makeMonthlySummary({ month: "2025-03" })} />);
    expect(screen.getByText(/March 2025/i)).toBeInTheDocument();
  });

  it("renders income, bills, and available figures", () => {
    render(
      <MonthCard
        summary={makeMonthlySummary({
          total_income: "2000.00",
          total_bills: "800.00",
          available: "1200.00",
        })}
      />,
    );
    expect(screen.getByText("$2,000.00")).toBeInTheDocument();
    expect(screen.getByText("−$800.00")).toBeInTheDocument();
    expect(screen.getByText("$1,200.00")).toBeInTheDocument();
  });

  it("shows 'Available' label when not overspent", () => {
    render(<MonthCard summary={makeMonthlySummary({ available: "100.00" })} />);
    expect(screen.getByText("Available")).toBeInTheDocument();
  });

  it("shows 'Overspent' label when available is negative", () => {
    render(
      <MonthCard
        summary={makeMonthlySummary({
          total_income: "1000.00",
          total_bills: "1200.00",
          available: "-200.00",
        })}
      />,
    );
    expect(screen.getByText("Overspent")).toBeInTheDocument();
  });

  it("applies overspent CSS class when available is negative", () => {
    const { container } = render(
      <MonthCard
        summary={makeMonthlySummary({ available: "-50.00" })}
      />,
    );
    expect(container.querySelector(".month-card--overspent")).toBeInTheDocument();
  });

  it("applies green color class when available ≥20% of income", () => {
    const { container } = render(
      <MonthCard
        summary={makeMonthlySummary({
          total_income: "1000.00",
          available: "200.00",
        })}
      />,
    );
    expect(
      container.querySelector(".month-card__value--green"),
    ).toBeInTheDocument();
  });

  it("applies amber color class when available <20% of income", () => {
    const { container } = render(
      <MonthCard
        summary={makeMonthlySummary({
          total_income: "1000.00",
          available: "150.00",
        })}
      />,
    );
    expect(
      container.querySelector(".month-card__value--amber"),
    ).toBeInTheDocument();
  });

  it("is collapsed by default", () => {
    const summary = makeMonthlySummary({
      categories: [makeMonthlyCategoryGroup({ category: "housing" })],
    });
    render(<MonthCard summary={summary} />);
    expect(screen.queryByText("Housing")).not.toBeInTheDocument();
  });

  it("expands when clicked", async () => {
    const user = userEvent.setup();
    const summary = makeMonthlySummary({
      categories: [makeMonthlyCategoryGroup({ category: "housing" })],
    });
    render(<MonthCard summary={summary} />);
    await user.click(screen.getByRole("button", { name: /january 2025/i }));
    expect(screen.getByText("Housing")).toBeInTheDocument();
  });

  it("shows 'No bills this month' when categories is empty", async () => {
    const user = userEvent.setup();
    render(<MonthCard summary={makeMonthlySummary({ categories: [] })} />);
    await user.click(screen.getByRole("button", { name: /january 2025/i }));
    expect(screen.getByText(/no bills this month/i)).toBeInTheDocument();
  });

  it("shows category headings and subtotals when expanded", async () => {
    const user = userEvent.setup();
    const summary = makeMonthlySummary({
      categories: [
        makeMonthlyCategoryGroup({
          category: "housing",
          subtotal: "900.00",
        }),
        makeMonthlyCategoryGroup({
          category: "utilities",
          subtotal: "80.00",
          bills: [
            makeMonthlyBillItem({
              bill_id: 2,
              name: "Electric",
              amount: "80.00",
              category: "utilities",
            }),
          ],
        }),
      ],
    });
    render(<MonthCard summary={summary} />);
    await user.click(screen.getByRole("button", { name: /january 2025/i }));
    expect(screen.getByRole("heading", { name: "Housing" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Utilities" })).toBeInTheDocument();
  });

  it("shows bill names, due dates, and amounts when expanded", async () => {
    const user = userEvent.setup();
    const summary = makeMonthlySummary({
      categories: [
        makeMonthlyCategoryGroup({
          subtotal: "1500.00",
          bills: [
            makeMonthlyBillItem({
              name: "Rent",
              due_date: "2025-01-01",
              amount: "900.00",
            }),
          ],
        }),
      ],
    });
    render(<MonthCard summary={summary} />);
    await user.click(screen.getByRole("button", { name: /january 2025/i }));
    expect(screen.getByText("Rent")).toBeInTheDocument();
    expect(screen.getByText("$900.00")).toBeInTheDocument();
  });

  it("shows ~ indicator for variable bills", async () => {
    const user = userEvent.setup();
    const summary = makeMonthlySummary({
      categories: [
        makeMonthlyCategoryGroup({
          bills: [makeMonthlyBillItem({ is_variable: true })],
        }),
      ],
    });
    render(<MonthCard summary={summary} />);
    await user.click(screen.getByRole("button", { name: /january 2025/i }));
    expect(screen.getByText("~")).toBeInTheDocument();
  });

  it("uses the actual amount when one is recorded", async () => {
    const user = userEvent.setup();
    const summary = makeMonthlySummary({
      categories: [
        makeMonthlyCategoryGroup({
          bills: [
            makeMonthlyBillItem({
              amount: "100.00",
              actual_amount: "75.00",
              status: "paid",
            }),
          ],
        }),
      ],
    });
    render(<MonthCard summary={summary} />);
    await user.click(screen.getByRole("button", { name: /january 2025/i }));
    expect(screen.getByText("$75.00")).toBeInTheDocument();
    expect(screen.queryByText("$100.00")).not.toBeInTheDocument();
  });

  it("marks a paid bill with a paid tag", async () => {
    const user = userEvent.setup();
    const summary = makeMonthlySummary({
      categories: [
        makeMonthlyCategoryGroup({
          bills: [makeMonthlyBillItem({ status: "paid" })],
        }),
      ],
    });
    render(<MonthCard summary={summary} />);
    await user.click(screen.getByRole("button", { name: /january 2025/i }));
    expect(screen.getByText("paid")).toBeInTheDocument();
  });

  it("marks a skipped bill with a skipped tag and strike styling", async () => {
    const user = userEvent.setup();
    const summary = makeMonthlySummary({
      categories: [
        makeMonthlyCategoryGroup({
          bills: [makeMonthlyBillItem({ status: "skipped" })],
        }),
      ],
    });
    const { container } = render(<MonthCard summary={summary} />);
    await user.click(screen.getByRole("button", { name: /january 2025/i }));
    expect(screen.getByText("skipped")).toBeInTheDocument();
    expect(
      container.querySelector(".month-card__bill-item--skipped"),
    ).toBeInTheDocument();
  });
});
