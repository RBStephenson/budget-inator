import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Link } from "../src/components/Link";

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("Link", () => {
  it("renders an anchor with the correct href", () => {
    render(<Link href="/bills">Bills</Link>);
    const a = screen.getByRole("link", { name: "Bills" });
    expect(a).toHaveAttribute("href", "/bills");
  });

  it("calls history.pushState and dispatches popstate on click", async () => {
    const user = userEvent.setup();
    const pushState = vi.spyOn(history, "pushState");
    const popstate = vi.fn();
    window.addEventListener("popstate", popstate);

    render(<Link href="/bills">Bills</Link>);
    await user.click(screen.getByRole("link", { name: "Bills" }));

    expect(pushState).toHaveBeenCalledWith({}, "", "/bills");
    expect(popstate).toHaveBeenCalledOnce();

    window.removeEventListener("popstate", popstate);
  });

  it("does not call pushState when Ctrl is held", async () => {
    const user = userEvent.setup();
    const pushState = vi.spyOn(history, "pushState");

    render(<Link href="/bills">Bills</Link>);
    await user.keyboard("{Control>}");
    await user.click(screen.getByRole("link", { name: "Bills" }));
    await user.keyboard("{/Control}");

    expect(pushState).not.toHaveBeenCalled();
  });

  it("passes extra props through to the anchor", () => {
    render(
      <Link href="/settings" className="app-nav__link" aria-label="Go to settings">
        Settings
      </Link>,
    );
    const a = screen.getByRole("link", { name: "Go to settings" });
    expect(a).toHaveClass("app-nav__link");
  });

  it("calls a custom onClick handler in addition to navigating", async () => {
    const user = userEvent.setup();
    vi.spyOn(history, "pushState");
    const onClick = vi.fn();

    render(<Link href="/bills" onClick={onClick}>Bills</Link>);
    await user.click(screen.getByRole("link", { name: "Bills" }));

    expect(onClick).toHaveBeenCalledOnce();
  });
});
