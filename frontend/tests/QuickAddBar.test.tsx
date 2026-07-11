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
});
