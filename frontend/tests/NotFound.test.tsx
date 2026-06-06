import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NotFound } from "../src/components/NotFound";

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("NotFound", () => {
  it("renders a page-not-found heading", () => {
    render(<NotFound />);
    expect(screen.getByRole("heading", { name: /page not found/i })).toBeInTheDocument();
  });

  it("renders a link back to the dashboard", () => {
    render(<NotFound />);
    expect(screen.getByRole("link", { name: /go to dashboard/i })).toHaveAttribute("href", "/");
  });

  it("navigates to / when the dashboard link is clicked", async () => {
    const user = userEvent.setup();
    const pushState = vi.spyOn(history, "pushState");

    render(<NotFound />);
    await user.click(screen.getByRole("link", { name: /go to dashboard/i }));

    expect(pushState).toHaveBeenCalledWith({}, "", "/");
  });
});
