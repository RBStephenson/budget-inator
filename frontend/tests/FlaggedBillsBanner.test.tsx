import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { FlaggedBillsBanner } from "../src/components/FlaggedBillsBanner";
import { makeBill, makePeriod } from "./fixtures";

describe("FlaggedBillsBanner", () => {
  it("renders nothing when there are no flagged bills", () => {
    const { container } = render(
      <FlaggedBillsBanner periods={[makePeriod()]} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders a banner when at least one bill is late_flagged", () => {
    const period = makePeriod({
      flagged_bill_count: 1,
      assigned_bills: [makeBill({ status: "late_flagged", name: "Old Bill" })],
    });
    render(<FlaggedBillsBanner periods={[period]} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/1 bill cannot be paid on time/i)).toBeInTheDocument();
  });

  it("shows the flagged bill name in the list", () => {
    const period = makePeriod({
      flagged_bill_count: 1,
      assigned_bills: [makeBill({ status: "late_flagged", name: "Old Bill" })],
    });
    render(<FlaggedBillsBanner periods={[period]} />);
    expect(screen.getByText("Old Bill")).toBeInTheDocument();
  });

  it("pluralises correctly for multiple flagged bills", () => {
    const period = makePeriod({
      flagged_bill_count: 2,
      assigned_bills: [
        makeBill({ bill_id: 1, status: "late_flagged", name: "Bill A", due_date: "2025-01-01" }),
        makeBill({ bill_id: 2, status: "late_flagged", name: "Bill B", due_date: "2025-01-02" }),
      ],
    });
    render(<FlaggedBillsBanner periods={[period]} />);
    expect(screen.getByText(/2 bills cannot be paid on time/i)).toBeInTheDocument();
  });

  it("does not include on_time bills in the banner", () => {
    const period = makePeriod({
      flagged_bill_count: 1,
      assigned_bills: [
        makeBill({ bill_id: 1, status: "late_flagged", name: "Late Bill", due_date: "2024-10-01" }),
        makeBill({ bill_id: 2, status: "on_time", name: "Fine Bill", due_date: "2025-01-05" }),
      ],
    });
    render(<FlaggedBillsBanner periods={[period]} />);
    expect(screen.getByText("Late Bill")).toBeInTheDocument();
    expect(screen.queryByText("Fine Bill")).not.toBeInTheDocument();
  });
});
