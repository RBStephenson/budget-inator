import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { QuickAddBar } from "../src/components/QuickAddBar";
import { ToastProvider } from "../src/context/ToastContext";
import { ToastContainer } from "../src/components/ToastContainer";

function renderWithToast(ui: React.ReactElement) {
  return render(
    <ToastProvider>
      {ui}
      <ToastContainer />
    </ToastProvider>,
  );
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("QuickAddBar", () => {
  it("disables Add until name and amount are filled in", async () => {
    const user = userEvent.setup();
    renderWithToast(<QuickAddBar onAdded={vi.fn()} onOpenFullForm={vi.fn()} />);

    expect(screen.getByRole("button", { name: /^add$/i })).toBeDisabled();

    await user.type(screen.getByLabelText(/bill name/i), "Gym");
    expect(screen.getByRole("button", { name: /^add$/i })).toBeDisabled();

    await user.type(screen.getByLabelText(/amount/i), "40");
    expect(screen.getByRole("button", { name: /^add$/i })).not.toBeDisabled();
  });

  it("disables Add for a $0 amount (BI-27)", async () => {
    const user = userEvent.setup();
    renderWithToast(<QuickAddBar onAdded={vi.fn()} onOpenFullForm={vi.fn()} />);

    await user.type(screen.getByLabelText(/bill name/i), "Gym");
    await user.type(screen.getByLabelText(/amount/i), "0");
    expect(screen.getByRole("button", { name: /^add$/i })).toBeDisabled();
  });

  it("posts a monthly bill and calls onAdded, clearing the form", async () => {
    const user = userEvent.setup();
    const onAdded = vi.fn();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: 5 }),
    } as Response);

    renderWithToast(<QuickAddBar onAdded={onAdded} onOpenFullForm={vi.fn()} />);

    await user.type(screen.getByLabelText(/bill name/i), "Gym");
    await user.type(screen.getByLabelText(/amount/i), "40");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/bills"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(onAdded).toHaveBeenCalledOnce();
    expect(screen.getByLabelText(/bill name/i)).toHaveValue("");
  });

  it("shows an error toast when the request fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    } as Response);

    renderWithToast(<QuickAddBar onAdded={vi.fn()} onOpenFullForm={vi.fn()} />);
    await user.type(screen.getByLabelText(/bill name/i), "Gym");
    await user.type(screen.getByLabelText(/amount/i), "40");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    expect(await screen.findByText(/could not add the bill/i)).toBeInTheDocument();
  });

  it("calls onOpenFullForm when the link is clicked", async () => {
    const user = userEvent.setup();
    const onOpenFullForm = vi.fn();
    renderWithToast(<QuickAddBar onAdded={vi.fn()} onOpenFullForm={onOpenFullForm} />);

    await user.click(screen.getByRole("button", { name: /open full form/i }));
    expect(onOpenFullForm).toHaveBeenCalledOnce();
  });

  describe("with showScheduleFields", () => {
    it("shows a due-day input for monthly recurrence and a due-date input otherwise", async () => {
      const user = userEvent.setup();
      renderWithToast(
        <QuickAddBar onAdded={vi.fn()} onOpenFullForm={vi.fn()} showScheduleFields />,
      );

      expect(screen.getByLabelText(/due day/i)).toBeInTheDocument();
      expect(screen.queryByLabelText(/next due date/i)).not.toBeInTheDocument();

      await user.selectOptions(screen.getByLabelText(/recurrence/i), "weekly");

      expect(screen.queryByLabelText(/due day/i)).not.toBeInTheDocument();
      expect(screen.getByLabelText(/next due date/i)).toBeInTheDocument();
    });

    it("posts due_day for monthly bills", async () => {
      const user = userEvent.setup();
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => ({ id: 5 }),
      } as Response);

      renderWithToast(
        <QuickAddBar onAdded={vi.fn()} onOpenFullForm={vi.fn()} showScheduleFields />,
      );
      await user.type(screen.getByLabelText(/bill name/i), "Rent");
      await user.type(screen.getByLabelText(/^amount$/i), "900");
      await user.click(screen.getByRole("button", { name: /^add$/i }));

      const call = fetchSpy.mock.calls[0];
      const body = JSON.parse(String(call[1]?.body));
      expect(body.recurrence).toBe("monthly");
      expect(body.due_day).toBeTypeOf("number");
      expect(body.due_date).toBeUndefined();
    });
  });
});
