import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { BillRow } from "../src/components/BillRow";
import { makeBill } from "./fixtures";

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
});
