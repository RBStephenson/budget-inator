import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { HelpPage } from "../src/components/HelpPage";

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("HelpPage", () => {
  it("renders the help page heading", () => {
    render(<HelpPage />);
    expect(
      screen.getByRole("heading", { name: /budget-inator field guide/i }),
    ).toBeInTheDocument();
  });

  it("renders all major section headings", () => {
    render(<HelpPage />);
    expect(screen.getByRole("heading", { name: /first-time setup/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^dashboard$/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /managing bills/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /tracking payments/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /annual cost/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /pdf report/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^settings$/i })).toBeInTheDocument();
  });

  it("renders a back-to-dashboard link", () => {
    render(<HelpPage />);
    expect(screen.getByRole("link", { name: /dashboard/i })).toHaveAttribute("href", "/");
  });

  it("documents both semimonthly payday patterns", () => {
    render(<HelpPage />);
    expect(screen.getAllByText(/15th\/month-end/i).length).toBeGreaterThan(0);
  });

  it("documents unpaid bill carryover reminders", () => {
    render(<HelpPage />);
    expect(screen.getByText(/unpaid from previous period/i)).toBeInTheDocument();
    expect(screen.getByText(/original due date/i)).toBeInTheDocument();
    expect(screen.getByText(/not added to the current period/i)).toBeInTheDocument();
  });

  it("documents dashboard workflow controls", () => {
    render(<HelpPage />);
    expect(screen.getAllByText(/Quick Add/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/actual deposit or current balance/i)).toBeInTheDocument();
    expect(screen.getByText(/starting balance/i)).toBeInTheDocument();
    expect(screen.getByText(/Rebalance available funds/i)).toBeInTheDocument();
    expect(screen.getByText(/Past periods/i)).toBeInTheDocument();
  });

  it("documents bill table and occurrence controls", () => {
    render(<HelpPage />);
    expect(screen.getByText(/searched, filtered by category, sorted by name or/i)).toBeInTheDocument();
    expect(screen.getAllByText(/^Notes$/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/included in backups/i)).toBeInTheDocument();
    expect(screen.getByText(/Use .*Move/i)).toBeInTheDocument();
    expect(screen.getByText(/Reset move/i)).toBeInTheDocument();
  });

  it("documents report and backup contents", () => {
    render(<HelpPage />);
    expect(screen.getByText(/sinking-fund reserves/i)).toBeInTheDocument();
    expect(screen.getByText(/effective-dated bill history/i)).toBeInTheDocument();
    expect(screen.getByText(/adjusted pay dates/i)).toBeInTheDocument();
    expect(screen.getByText(/payday actuals/i)).toBeInTheDocument();
  });

  it("navigates to / when the back link is clicked", async () => {
    const user = userEvent.setup();
    const pushState = vi.spyOn(history, "pushState");
    render(<HelpPage />);
    await user.click(screen.getByRole("link", { name: /dashboard/i }));
    expect(pushState).toHaveBeenCalledWith({}, "", "/");
  });
});
