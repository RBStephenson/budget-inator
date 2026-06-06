import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../src/App";

beforeEach(() => {
  vi.restoreAllMocks();
  window.history.pushState({}, "", "/");
});

afterEach(() => {
  window.history.pushState({}, "", "/");
  vi.restoreAllMocks();
});

function mockScheduleFetch() {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => ({
      periods: [],
      summary: { from_date: "", to_date: "", period_count: 0, total_flagged_bills: 0 },
    }),
  } as Response);
}

function mockSettingsFetch() {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: false,
    status: 404,
    statusText: "Not Found",
    json: async () => ({}),
  } as Response);
}

describe("App", () => {
  it("renders the app title", async () => {
    mockScheduleFetch();
    render(<App />);
    await waitFor(() => expect(screen.queryByText(/loading/i)).not.toBeInTheDocument());
    expect(screen.getByText("Budget-inator")).toBeInTheDocument();
  });

  it("renders settings and help nav links on every page", async () => {
    mockScheduleFetch();
    render(<App />);
    await waitFor(() => expect(screen.queryByText(/loading/i)).not.toBeInTheDocument());
    expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: /^help$/i })).toHaveAttribute("href", "/help");
  });

  it("renders HelpPage when path is /help", () => {
    window.history.pushState({}, "", "/help");
    render(<App />);
    expect(screen.getByRole("heading", { name: /^help$/i })).toBeInTheDocument();
  });

  it("renders SettingsPage when path is /settings", async () => {
    window.history.pushState({}, "", "/settings");
    mockSettingsFetch();
    render(<App />);
    await waitFor(() =>
      expect(screen.queryByText(/loading settings/i)).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("heading", { name: /pay schedule/i })).toBeInTheDocument();
  });

  it("renders the not-found page for an unknown path", () => {
    window.history.pushState({}, "", "/does-not-exist");
    mockScheduleFetch();
    render(<App />);
    expect(screen.getByRole("heading", { name: /page not found/i })).toBeInTheDocument();
  });

  it("navigates to BillsPage without a full reload when the Add Bill link is clicked", async () => {
    const user = userEvent.setup();
    mockScheduleFetch();
    render(<App />);
    await waitFor(() => expect(screen.queryByText(/loading/i)).not.toBeInTheDocument());

    // Dashboard shows an "Add Bill" link that should client-side navigate
    const addBillLink = screen.getByRole("link", { name: /add bill/i });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    } as Response);
    await user.click(addBillLink);

    expect(window.location.pathname).toBe("/bills");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /^bills$/i })).toBeInTheDocument(),
    );
  });

  it("navigates back to the dashboard from the not-found page", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/does-not-exist");
    mockScheduleFetch();
    render(<App />);

    expect(screen.getByRole("heading", { name: /page not found/i })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: /go to dashboard/i }));

    expect(window.location.pathname).toBe("/");
    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: /page not found/i })).not.toBeInTheDocument(),
    );
  });
});
