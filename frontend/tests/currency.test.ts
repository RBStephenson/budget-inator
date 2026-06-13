import { describe, it, expect } from "vitest";
import { fmtCurrency } from "../src/utils/currency";

describe("fmtCurrency", () => {
  it("formats a positive number", () => {
    expect(fmtCurrency(1234.56)).toBe("$1,234.56");
  });

  it("formats a string input", () => {
    expect(fmtCurrency("500.00")).toBe("$500.00");
  });

  it("formats zero", () => {
    expect(fmtCurrency(0)).toBe("$0.00");
  });

  it("formats a negative value", () => {
    expect(fmtCurrency(-99.5)).toBe("-$99.50");
  });

  it("formats a string | number union (string | number)", () => {
    const val: string | number = 42;
    expect(fmtCurrency(val)).toBe("$42.00");
  });
});
