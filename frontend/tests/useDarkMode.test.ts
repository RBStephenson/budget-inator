import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { useDarkMode } from "../src/hooks/useDarkMode";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

afterEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("useDarkMode", () => {
  it("defaults to light mode when nothing is stored", () => {
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.dark).toBe(false);
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("reads a previously stored dark preference", () => {
    localStorage.setItem("budgetinator-dark", "1");
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.dark).toBe(true);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("toggle flips state, persists to localStorage, and updates the DOM attribute", () => {
    const { result } = renderHook(() => useDarkMode());

    act(() => result.current.toggle());
    expect(result.current.dark).toBe(true);
    expect(localStorage.getItem("budgetinator-dark")).toBe("1");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

    act(() => result.current.toggle());
    expect(result.current.dark).toBe(false);
    expect(localStorage.getItem("budgetinator-dark")).toBe("0");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });
});
