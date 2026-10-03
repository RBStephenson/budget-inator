import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { todayIso } from "../src/utils/date";

// Pin a zone west of UTC: CI runs in UTC, where local and UTC dates always
// agree and this test could not tell the two implementations apart.
beforeEach(() => {
  vi.stubEnv("TZ", "America/New_York");
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

describe("todayIso", () => {
  it("returns the local calendar date, not the UTC one", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    // 11:30 PM in New York is already the next day in UTC - exactly the case
    // toISOString().slice(0, 10) gets wrong.
    vi.setSystemTime(new Date("2026-10-04T03:30:00Z"));

    expect(todayIso()).toBe("2026-10-03");
  });
});
