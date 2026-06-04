import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../src/App";

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      periods: [],
      summary: { from_date: "", to_date: "", period_count: 0, total_flagged_bills: 0 },
    }),
  } as Response);
});

describe("App", () => {
  it("renders the app title", async () => {
    render(<App />);
    // Wait for Dashboard to settle its async state before assertions
    await waitFor(() => expect(screen.queryByText(/loading/i)).not.toBeInTheDocument());
    expect(screen.getByText("Budget-inator")).toBeInTheDocument();
  });
});
