import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../src/App";

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

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

  it("renders a settings nav link on every page", async () => {
    mockScheduleFetch();
    render(<App />);
    await waitFor(() => expect(screen.queryByText(/loading/i)).not.toBeInTheDocument());
    expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute("href", "/settings");
  });

  it("renders SettingsPage when path is /settings", async () => {
    window.history.pushState({}, "", "/settings");
    mockSettingsFetch();
    render(<App />);
    await waitFor(() =>
      expect(screen.queryByText(/loading settings/i)).not.toBeInTheDocument(),
    );
    expect(screen.getByText(/pay schedule/i)).toBeInTheDocument();
    window.history.pushState({}, "", "/");
  });
});
