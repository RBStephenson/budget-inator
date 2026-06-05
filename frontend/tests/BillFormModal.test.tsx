import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BillFormModal } from "../src/components/BillFormModal";
import { makeApiBill } from "./fixtures";

function mockFetch(ok = true) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status: ok ? 201 : 422,
    statusText: ok ? "Created" : "Unprocessable Entity",
    json: async () => makeApiBill(),
  } as Response);
}

beforeEach(() => vi.restoreAllMocks());

describe("BillFormModal — add mode", () => {
  it("renders the add bill title", () => {
    render(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Add bill" })).toBeInTheDocument();
  });

  it("shows the due-day field by default (monthly recurrence)", () => {
    render(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    expect(screen.getByLabelText(/due day/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/due date/i)).not.toBeInTheDocument();
  });

  it("switches to due-date field when recurrence changes to biweekly", async () => {
    render(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    await userEvent.selectOptions(screen.getByLabelText(/recurrence/i), "biweekly");
    expect(screen.queryByLabelText(/due day/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/due date/i)).toBeInTheDocument();
  });

  it("shows validation errors when submitting an empty form", async () => {
    render(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /add bill/i }));
    expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/enter a positive amount/i)).toBeInTheDocument();
    expect(screen.getByText(/category is required/i)).toBeInTheDocument();
  });

  it("calls onSave after a successful submit", async () => {
    mockFetch(true);
    const onSave = vi.fn();
    render(<BillFormModal onSave={onSave} onClose={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/^name/i), "Rent");
    await userEvent.type(screen.getByLabelText(/^amount/i), "1200");
    await userEvent.selectOptions(screen.getByLabelText(/category/i), "housing");
    await userEvent.type(screen.getByLabelText(/due day/i), "1");
    await userEvent.click(screen.getByRole("button", { name: /add bill/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
  });

  it("calls onClose when cancel is clicked", async () => {
    const onClose = vi.fn();
    render(<BillFormModal onSave={vi.fn()} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("shows the estimated label when is_variable is toggled on", async () => {
    render(<BillFormModal onSave={vi.fn()} onClose={vi.fn()} />);
    await userEvent.click(screen.getByLabelText(/variable amount/i));
    expect(screen.getByText("(estimated)")).toBeInTheDocument();
  });
});

describe("BillFormModal — edit mode", () => {
  it("renders the edit bill title", () => {
    render(
      <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { name: "Edit bill" })).toBeInTheDocument();
  });

  it("pre-fills the name field", () => {
    render(
      <BillFormModal
        bill={makeApiBill({ name: "Mortgage" })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByDisplayValue("Mortgage")).toBeInTheDocument();
  });

  it("pre-fills the category dropdown", () => {
    render(
      <BillFormModal
        bill={makeApiBill({ category: "housing" })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(
      (screen.getByLabelText(/category/i) as HTMLSelectElement).value,
    ).toBe("housing");
  });

  it("shows the due-date field when editing a biweekly bill", () => {
    render(
      <BillFormModal
        bill={makeApiBill({ recurrence: "biweekly", due_day: null, due_date: "2025-01-03" })}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByLabelText(/due date/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/due day/i)).not.toBeInTheDocument();
  });

  it("shows a server error when the API call fails", async () => {
    mockFetch(false);
    render(
      <BillFormModal bill={makeApiBill()} onSave={vi.fn()} onClose={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));
    await waitFor(() =>
      expect(screen.getByText(/failed to save bill/i)).toBeInTheDocument(),
    );
  });
});
