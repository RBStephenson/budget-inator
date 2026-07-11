import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ConfirmDialog } from "../src/components/ConfirmDialog";

describe("ConfirmDialog", () => {
  it("renders the message", () => {
    render(
      <ConfirmDialog
        message="Are you sure?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Are you sure?")).toBeInTheDocument();
  });

  it("calls onConfirm when the confirm button is clicked", async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog message="Sure?" onConfirm={onConfirm} onCancel={vi.fn()} />,
    );
    await userEvent.click(screen.getByText("Confirm"));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("calls onCancel when the cancel button is clicked", async () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog message="Sure?" onConfirm={vi.fn()} onCancel={onCancel} />,
    );
    await userEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("renders a custom confirm label", () => {
    render(
      <ConfirmDialog
        message="Sure?"
        confirmLabel="Delete it"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Delete it")).toBeInTheDocument();
  });

  it("renders a title when provided", () => {
    render(
      <ConfirmDialog
        title="Deactivate this bill?"
        message="It will be hidden from the schedule."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Deactivate this bill?" }),
    ).toBeInTheDocument();
  });

  describe("destructive variant", () => {
    it("disables the confirm button until DELETE is typed exactly", async () => {
      const user = userEvent.setup();
      const onConfirm = vi.fn();
      render(
        <ConfirmDialog
          message="This cannot be undone."
          confirmLabel="Delete everything"
          onConfirm={onConfirm}
          onCancel={vi.fn()}
          destructive
        />,
      );

      const confirmButton = screen.getByRole("button", { name: "Delete everything" });
      expect(confirmButton).toBeDisabled();

      const gate = screen.getByLabelText(/type delete to confirm/i);
      await user.type(gate, "delete");
      expect(confirmButton).toBeDisabled();

      await user.clear(gate);
      await user.type(gate, "DELETE");
      expect(confirmButton).not.toBeDisabled();

      await user.click(confirmButton);
      expect(onConfirm).toHaveBeenCalledOnce();
    });

    it("does not show the DELETE gate for a standard (non-destructive) dialog", () => {
      render(
        <ConfirmDialog message="Sure?" onConfirm={vi.fn()} onCancel={vi.fn()} />,
      );
      expect(screen.queryByLabelText(/type delete to confirm/i)).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Confirm" })).not.toBeDisabled();
    });
  });

  describe("multi-item confirm (children slot)", () => {
    it("renders extra content between the message and the action buttons", () => {
      render(
        <ConfirmDialog message="Preview changes" onConfirm={vi.fn()} onCancel={vi.fn()}>
          <ul>
            <li>Move A</li>
            <li>Move B</li>
          </ul>
        </ConfirmDialog>,
      );
      expect(screen.getByText("Move A")).toBeInTheDocument();
      expect(screen.getByText("Move B")).toBeInTheDocument();
    });

    it("respects an externally-controlled confirmDisabled prop", () => {
      render(
        <ConfirmDialog
          message="Preview changes"
          confirmLabel="Apply moves"
          onConfirm={vi.fn()}
          onCancel={vi.fn()}
          confirmDisabled
        />,
      );
      expect(screen.getByRole("button", { name: "Apply moves" })).toBeDisabled();
    });
  });
});
