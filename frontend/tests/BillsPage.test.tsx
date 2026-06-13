import { render as rtlRender, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { BillsPage } from "../src/components/BillsPage";
import { ToastContainer } from "../src/components/ToastContainer";
import { ToastProvider } from "../src/context/ToastContext";
import { makeApiBill } from "./fixtures";

// BillsPage calls useToast(); wrap every render in a ToastProvider with a
// ToastContainer so error toasts can be asserted.
function render(ui: React.ReactElement) {
  return rtlRender(
    <ToastProvider>
      {ui}
      <ToastContainer />
    </ToastProvider>,
  );
}

function mockListBills(bills: ReturnType<typeof makeApiBill>[], ok = true) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Internal Server Error",
    json: async () => bills,
  } as Response);
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("BillsPage", () => {
  it("shows a loading state initially", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    render(<BillsPage />);
    expect(screen.getByText(/loading bills/i)).toBeInTheDocument();
  });

  it("shows an error state when the API fails", async () => {
    mockListBills([], false);
    render(<BillsPage />);
    await waitFor(() =>
      expect(screen.getByText(/could not load bills/i)).toBeInTheDocument(),
    );
  });

  it("shows an empty state when there are no bills", async () => {
    mockListBills([]);
    render(<BillsPage />);
    await waitFor(() =>
      expect(screen.getByText(/no bills yet/i)).toBeInTheDocument(),
    );
  });

  it("renders the bill table when bills are loaded", async () => {
    mockListBills([makeApiBill({ name: "Rent" })]);
    render(<BillsPage />);
    await waitFor(() => expect(screen.getByText("Rent")).toBeInTheDocument());
  });

  it("opens the add modal when the Add Bill button is clicked", async () => {
    mockListBills([]);
    render(<BillsPage />);
    await waitFor(() =>
      expect(screen.getByText(/no bills yet/i)).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /\+ add bill/i }));
    expect(screen.getByRole("heading", { name: "Add bill" })).toBeInTheDocument();
  });

  it("opens the edit modal when Edit is clicked on a bill", async () => {
    mockListBills([makeApiBill({ name: "Rent" })]);
    render(<BillsPage />);
    await waitFor(() => expect(screen.getByText("Rent")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /edit rent/i }));
    expect(screen.getByText("Edit bill")).toBeInTheDocument();
  });

  it("shows the confirm dialog when Deactivate is clicked", async () => {
    mockListBills([makeApiBill({ name: "Rent" })]);
    render(<BillsPage />);
    await waitFor(() => expect(screen.getByText("Rent")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /deactivate rent/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/deactivate "Rent"/i)).toBeInTheDocument();
  });

  it("closes the confirm dialog when Cancel is clicked", async () => {
    mockListBills([makeApiBill({ name: "Rent" })]);
    render(<BillsPage />);
    await waitFor(() => expect(screen.getByText("Rent")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /deactivate rent/i }));
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows an error toast and keeps the dialog open when deactivate fails", async () => {
    // GET /bills succeeds; the deactivate PATCH fails
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "PATCH") {
        return Promise.resolve({
          ok: false,
          status: 500,
          statusText: "Internal Server Error",
          json: async () => ({}),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => [makeApiBill({ name: "Rent" })],
      } as Response);
    });
    render(<BillsPage />);
    await waitFor(() => expect(screen.getByText("Rent")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /deactivate rent/i }));
    await userEvent.click(screen.getByRole("button", { name: "Deactivate" }));
    await waitFor(() =>
      expect(
        screen.getByText(/could not deactivate "Rent"/i),
      ).toBeInTheDocument(),
    );
    // Dialog stays open so the user can retry or cancel
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("renders the back-to-dashboard link", async () => {
    mockListBills([]);
    render(<BillsPage />);
    await waitFor(() =>
      expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument(),
    );
  });

});
