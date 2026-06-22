import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { HelpPage } from "../src/components/HelpPage";

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("HelpPage", () => {
  it("renders the Help heading", () => {
    render(<HelpPage />);
    expect(screen.getByRole("heading", { name: /^help$/i })).toBeInTheDocument();
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

  it("navigates to / when the back link is clicked", async () => {
    const user = userEvent.setup();
    const pushState = vi.spyOn(history, "pushState");
    render(<HelpPage />);
    await user.click(screen.getByRole("link", { name: /dashboard/i }));
    expect(pushState).toHaveBeenCalledWith({}, "", "/");
  });
});
