import { render as rtlRender, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PeriodCard } from "../src/components/PeriodCard";
import { ToastProvider } from "../src/context/ToastContext";
import { makeBill, makePeriod } from "./fixtures";

// PeriodCard renders BillRow, which calls useToast(); wrap every render in
// a ToastProvider.
function render(ui: React.ReactElement) {
  return rtlRender(<ToastProvider>{ui}</ToastProvider>);
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

function mockFetch(ok = true) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Internal Server Error",
    json: async () => ({}),
  } as Response);
}

describe("PeriodCard", () => {
  it("renders the period date range", () => {
    const { container } = render(<PeriodCard period={makePeriod()} />);
    const range = container.querySelector(".period-card__range");
    expect(range?.textContent).toMatch(/Jan 3/);
    expect(range?.textContent).toMatch(/Jan 16/);
  });

  it("shows 'Current period' label when isHero=true", () => {
    render(<PeriodCard period={makePeriod()} isHero />);
    expect(screen.getByText("Current period")).toBeInTheDocument();
  });

  it("shows 'Upcoming' label when isHero=false", () => {
    render(<PeriodCard period={makePeriod()} />);
    expect(screen.getByText("Upcoming")).toBeInTheDocument();
  });

  it("shows today badge on hero card", () => {
    const { container } = render(<PeriodCard period={makePeriod()} isHero />);
    expect(container.querySelector(".period-card__today-badge")).toBeInTheDocument();
  });

  it("does not show today badge on upcoming card", () => {
    const { container } = render(<PeriodCard period={makePeriod()} />);
    expect(container.querySelector(".period-card__today-badge")).not.toBeInTheDocument();
  });

  it("renders progress bar on hero card", () => {
    const { container } = render(<PeriodCard period={makePeriod()} isHero />);
    expect(container.querySelector(".period-card__progress-wrap")).toBeInTheDocument();
  });

  it("does not render progress bar on upcoming card", () => {
    const { container } = render(<PeriodCard period={makePeriod()} />);
    expect(container.querySelector(".period-card__progress-wrap")).not.toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: /upcoming/i }));
    expect(screen.getByText("Rent")).toBeInTheDocument();
  });

  it("collapses on second click", async () => {
    const user = userEvent.setup();
    const period = makePeriod({ assigned_bills: [makeBill({ name: "Rent" })] });
    render(<PeriodCard period={period} isHero />);
    const btn = screen.getByRole("button", { name: /current period/i });
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

  it("applies green balance color when remaining is ≥20% of opening", () => {
    const { container } = render(
      <PeriodCard
        period={makePeriod({ opening_balance: "1000.00", remaining_balance: "200.00" })}
      />,
    );
    expect(
      container.querySelector(".period-card__balance-value--green"),
    ).toBeInTheDocument();
  });

  it("applies amber balance color when remaining is <20% of opening", () => {
    const { container } = render(
      <PeriodCard
        period={makePeriod({ opening_balance: "1000.00", remaining_balance: "150.00" })}
      />,
    );
    expect(
      container.querySelector(".period-card__balance-value--amber"),
    ).toBeInTheDocument();
  });

  it("shows flagged badge when period has flagged bills", () => {
    render(<PeriodCard period={makePeriod({ flagged_bill_count: 2 })} />);
    expect(screen.getByLabelText(/2 late bill/i)).toBeInTheDocument();
  });

  it("does not show flagged badge when no flagged bills", () => {
    render(<PeriodCard period={makePeriod({ flagged_bill_count: 0 })} />);
    expect(screen.queryByLabelText(/late bill/i)).not.toBeInTheDocument();
  });

  it("shows a manual move indicator when bills were manually moved", () => {
    render(
      <PeriodCard
        period={makePeriod({
          assigned_bills: [
            makeBill({ bill_id: 1, name: "Rent" }),
            makeBill({
              bill_id: 2,
              name: "Internet",
              placement_source: "manual",
              manual_pay_date: "2025-01-03",
            }),
          ],
        })}
      />,
    );

    expect(screen.getByLabelText(/1 manually moved bill/i)).toBeInTheDocument();
    expect(screen.getByText("1 bill manually moved")).toBeInTheDocument();
  });

  it("does not show a manual move indicator when placement is inferred", () => {
    render(
      <PeriodCard
        period={makePeriod({
          assigned_bills: [makeBill({ placement_source: "inferred" })],
        })}
      />,
    );

    expect(screen.queryByLabelText(/manually moved bill/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/manually moved/i)).not.toBeInTheDocument();
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

describe("PeriodCard - explicit rebalance", () => {
  it("shows a rebalance button when the period has available funds", () => {
    render(<PeriodCard period={makePeriod({ remaining_balance: "300.00" })} />);
    expect(
      screen.getByRole("button", { name: /rebalance available funds/i }),
    ).toBeInTheDocument();
  });

  it("does not show a rebalance button when the period is overspent", () => {
    render(<PeriodCard period={makePeriod({ remaining_balance: "-10.00" })} />);
    expect(
      screen.queryByRole("button", { name: /rebalance available funds/i }),
    ).not.toBeInTheDocument();
  });

  it("previews and applies rebalance moves", async () => {
    const onRefetch = vi.fn();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => ({
          source_pay_date: "2025-01-03",
          source_remaining_before: "1500.00",
          source_remaining_after: "1000.00",
          moves: [
            {
              bill_id: 2,
              name: "Internet",
              due_date: "2025-01-20",
              amount: "500.00",
              from_pay_date: "2025-01-17",
              to_pay_date: "2025-01-03",
              from_period_remaining_before: "-600.00",
              from_period_remaining_after: "-100.00",
              source_remaining_before: "1500.00",
              source_remaining_after: "1000.00",
              reason: "Internet is due 2025-01-20 and funds are available.",
            },
          ],
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
        statusText: "No Content",
        json: async () => ({}),
      } as Response);

    render(
      <PeriodCard
        period={makePeriod({
          original_pay_date: "2025-01-03",
          remaining_balance: "1500.00",
        })}
        onRefetch={onRefetch}
      />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: /rebalance available funds/i }),
    );

    await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
    expect(screen.getByText("Internet")).toBeInTheDocument();
    expect(
      screen.getByText(/available changes from \$1,500.00 to \$1,000.00/i),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /apply moves/i }));
    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());

    expect(fetchSpy.mock.calls[0][0]).toContain("/schedule/rebalance-preview");
    expect(fetchSpy.mock.calls[1][0]).toContain("/schedule/rebalance-apply");
  });

  it("shows an empty preview when no future bills are eligible", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        source_pay_date: "2025-01-03",
        source_remaining_before: "300.00",
        source_remaining_after: "300.00",
        moves: [],
      }),
    } as Response);

    render(<PeriodCard period={makePeriod({ remaining_balance: "300.00" })} />);
    await userEvent.click(
      screen.getByRole("button", { name: /rebalance available funds/i }),
    );

    await waitFor(() =>
      expect(screen.getByText(/no eligible future bills/i)).toBeInTheDocument(),
    );
  });
});

describe("PeriodCard — category grouping", () => {
  it("renders a category heading for each category present", () => {
    const period = makePeriod({
      assigned_bills: [
        makeBill({ bill_id: 1, name: "Rent", category: "housing" }),
        makeBill({ bill_id: 2, name: "Electric", category: "utilities" }),
      ],
    });
    render(<PeriodCard period={period} isHero />);
    expect(screen.getByRole("heading", { name: "Housing" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Utilities" })).toBeInTheDocument();
  });

  it("renders only one heading per category even with multiple bills", () => {
    const period = makePeriod({
      assigned_bills: [
        makeBill({ bill_id: 1, name: "Rent", category: "housing" }),
        makeBill({ bill_id: 2, name: "Mortgage", category: "housing" }),
      ],
    });
    render(<PeriodCard period={period} isHero />);
    expect(screen.getAllByRole("heading", { name: "Housing" })).toHaveLength(1);
  });

  it("does not render a heading for absent categories", () => {
    const period = makePeriod({
      assigned_bills: [makeBill({ category: "housing" })],
    });
    render(<PeriodCard period={period} isHero />);
    expect(screen.queryByRole("heading", { name: "Utilities" })).not.toBeInTheDocument();
  });

  it("renders categories in canonical order (housing before utilities before subscriptions)", () => {
    const period = makePeriod({
      assigned_bills: [
        makeBill({ bill_id: 1, name: "Netflix", category: "subscriptions" }),
        makeBill({ bill_id: 2, name: "Electric", category: "utilities" }),
        makeBill({ bill_id: 3, name: "Rent", category: "housing" }),
      ],
    });
    const { container } = render(<PeriodCard period={period} isHero />);
    const headings = Array.from(container.querySelectorAll(".period-card__category-heading"));
    const texts = headings.map((h) => h.textContent);
    const housingIdx = texts.indexOf("Housing");
    const utilitiesIdx = texts.indexOf("Utilities");
    const subscriptionsIdx = texts.indexOf("Subscriptions");
    expect(housingIdx).toBeLessThan(utilitiesIdx);
    expect(utilitiesIdx).toBeLessThan(subscriptionsIdx);
  });

  it("bills within a category group are visible under that heading", () => {
    const period = makePeriod({
      assigned_bills: [
        makeBill({ bill_id: 1, name: "Rent", category: "housing" }),
        makeBill({ bill_id: 2, name: "Electric", category: "utilities" }),
      ],
    });
    render(<PeriodCard period={period} isHero />);
    expect(screen.getByText("Rent")).toBeInTheDocument();
    expect(screen.getByText("Electric")).toBeInTheDocument();
  });
});

describe("PeriodCard — pay date override", () => {
  it("shows the pay date in the payday row", () => {
    const { container } = render(<PeriodCard period={makePeriod({ pay_date: "2025-01-03" })} />);
    const row = container.querySelector(".period-card__payday-value");
    expect(row?.textContent).toMatch(/Jan 3/);
  });

  it("shows Edit pay date button", () => {
    render(<PeriodCard period={makePeriod()} />);
    expect(screen.getByRole("button", { name: /edit pay date/i })).toBeInTheDocument();
  });

  it("does not show adjusted indicator when not overridden", () => {
    render(<PeriodCard period={makePeriod({ is_overridden: false })} />);
    expect(screen.queryByLabelText(/pay date adjusted/i)).not.toBeInTheDocument();
  });

  it("shows adjusted indicator when overridden", () => {
    render(
      <PeriodCard
        period={makePeriod({ is_overridden: true, pay_date: "2025-01-02", original_pay_date: "2025-01-03" })}
      />,
    );
    expect(screen.getByLabelText(/pay date adjusted/i)).toBeInTheDocument();
  });

  it("shows Reset button only when overridden", () => {
    render(
      <PeriodCard
        period={makePeriod({ is_overridden: true, pay_date: "2025-01-02", original_pay_date: "2025-01-03" })}
      />,
    );
    expect(screen.getByRole("button", { name: /reset pay date/i })).toBeInTheDocument();
  });

  it("does not show Reset button when not overridden", () => {
    render(<PeriodCard period={makePeriod({ is_overridden: false })} />);
    expect(screen.queryByRole("button", { name: /reset pay date/i })).not.toBeInTheDocument();
  });

  it("reveals date input when Edit is clicked", async () => {
    render(<PeriodCard period={makePeriod()} />);
    await userEvent.click(screen.getByRole("button", { name: /edit pay date/i }));
    expect(screen.getByLabelText(/override pay date/i)).toBeInTheDocument();
  });

  it("hides input after cancel", async () => {
    render(<PeriodCard period={makePeriod()} />);
    await userEvent.click(screen.getByRole("button", { name: /edit pay date/i }));
    await userEvent.click(screen.getByRole("button", { name: /cancel pay date/i }));
    expect(screen.queryByLabelText(/override pay date/i)).not.toBeInTheDocument();
  });

  it("calls PUT override and onRefetch on confirm", async () => {
    mockFetch();
    const onRefetch = vi.fn();
    render(<PeriodCard period={makePeriod({ original_pay_date: "2025-01-03" })} onRefetch={onRefetch} />);
    await userEvent.click(screen.getByRole("button", { name: /edit pay date/i }));
    const input = screen.getByLabelText(/override pay date/i);
    await userEvent.clear(input);
    await userEvent.type(input, "2025-01-02");
    await userEvent.click(screen.getByRole("button", { name: /confirm pay date/i }));
    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
    const fetchMock = vi.mocked(globalThis.fetch);
    expect(fetchMock.mock.calls[0][0]).toContain("pay-period-overrides/2025-01-03");
    expect(fetchMock.mock.calls[0][1]?.method).toBe("PUT");
  });

  it("calls DELETE override and onRefetch on reset", async () => {
    mockFetch();
    const onRefetch = vi.fn();
    render(
      <PeriodCard
        period={makePeriod({ is_overridden: true, pay_date: "2025-01-02", original_pay_date: "2025-01-03" })}
        onRefetch={onRefetch}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /reset pay date/i }));
    await waitFor(() => expect(onRefetch).toHaveBeenCalledOnce());
    const fetchMock = vi.mocked(globalThis.fetch);
    expect(fetchMock.mock.calls[0][0]).toContain("pay-period-overrides/2025-01-03");
    expect(fetchMock.mock.calls[0][1]?.method).toBe("DELETE");
  });
});
