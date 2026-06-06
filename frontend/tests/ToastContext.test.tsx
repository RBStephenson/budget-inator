import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ToastContainer } from "../src/components/ToastContainer";
import { ToastProvider, useToast } from "../src/context/ToastContext";

function makeTestHarness(message = "Hello world", variant?: "success" | "error" | "info") {
  function Trigger() {
    const { addToast } = useToast();
    return (
      <button onClick={() => addToast(message, variant)}>Show toast</button>
    );
  }
  return render(
    <ToastProvider>
      <Trigger />
      <ToastContainer />
    </ToastProvider>,
  );
}

describe("ToastContext — basic behaviour", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("renders no toasts initially", () => {
    makeTestHarness();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a toast after addToast is called", async () => {
    makeTestHarness("Hello world", "info");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    expect(screen.getByRole("alert")).toHaveTextContent("Hello world");
  });

  it("auto-dismisses an info toast after 4 seconds", async () => {
    makeTestHarness("msg", "info");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(4000));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not dismiss before the timeout elapses", async () => {
    makeTestHarness("msg", "info");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    act(() => vi.advanceTimersByTime(3999));
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("dismisses manually when the dismiss button is clicked", async () => {
    makeTestHarness("msg", "info");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    await userEvent.click(
      screen.getByRole("button", { name: /dismiss notification/i }),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("stacks multiple toasts", async () => {
    makeTestHarness("msg", "info");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    expect(screen.getAllByRole("alert")).toHaveLength(3);
  });

  it("removes only the dismissed toast when multiple are shown", async () => {
    makeTestHarness("msg", "info");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    const dismissButtons = screen.getAllByRole("button", {
      name: /dismiss notification/i,
    });
    await userEvent.click(dismissButtons[0]);
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  });
});

describe("ToastContext — variant timing", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("auto-dismisses a success toast after 4 seconds", async () => {
    makeTestHarness("msg", "success");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    act(() => vi.advanceTimersByTime(4000));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("auto-dismisses an error toast after 6 seconds (not before)", async () => {
    makeTestHarness("msg", "error");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    act(() => vi.advanceTimersByTime(5999));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("applies toast--success class for success variant", async () => {
    makeTestHarness("msg", "success");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    expect(screen.getByRole("alert")).toHaveClass("toast--success");
  });

  it("applies toast--error class for error variant", async () => {
    makeTestHarness("msg", "error");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    expect(screen.getByRole("alert")).toHaveClass("toast--error");
  });

  it("applies toast--info class for info variant", async () => {
    makeTestHarness("msg", "info");
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    expect(screen.getByRole("alert")).toHaveClass("toast--info");
  });

  it("defaults to info variant when no variant is provided", async () => {
    function DefaultTrigger() {
      const { addToast } = useToast();
      return <button onClick={() => addToast("default")}>Show toast</button>;
    }
    render(
      <ToastProvider>
        <DefaultTrigger />
        <ToastContainer />
      </ToastProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: /show toast/i }));
    expect(screen.getByRole("alert")).toHaveClass("toast--info");
  });
});

describe("ToastContext — useToast outside provider", () => {
  it("throws when useToast is called outside a ToastProvider", () => {
    function Bad() {
      useToast();
      return null;
    }
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Bad />)).toThrow(
      "useToast must be used inside <ToastProvider>",
    );
    consoleSpy.mockRestore();
  });
});
