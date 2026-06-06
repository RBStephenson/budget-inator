import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { BillsPage } from "../src/components/BillsPage";
import { ToastProvider } from "../src/context/ToastContext";
import { makeApiBill } from "./fixtures";

// BillsPage opens BillFormModal, which calls useToast(); wrap renders that
// reach the modal in a ToastProvider.
function renderWithToast(ui: React.ReactElement) {
  return render(<ToastProvider>{ui}</ToastProvider>);
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
    renderWithToast(<BillsPage />);
    await waitFor(() =>
      expect(screen.getByText(/no bills yet/i)).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /\+ add bill/i }));
    expect(screen.getByRole("heading", { name: "Add bill" })).toBeInTheDocument();
  });

  it("opens the edit modal when Edit is clicked on a bill", async () => {
    mockListBills([makeApiBill({ name: "Rent" })]);
    renderWithToast(<BillsPage />);
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

  it("renders the back-to-dashboard link", async () => {
    mockListBills([]);
    render(<BillsPage />);
    await waitFor(() =>
      expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument(),
    );
  });
});
