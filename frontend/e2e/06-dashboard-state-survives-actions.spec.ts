import { test, expect } from "@playwright/test";

// Runs last, against the state 04 restored and 05 left: Streaming is still
// pending in the current period. A bill action refetches the shared schedule;
// that refetch must not tear down and remount the Dashboard, or every piece of
// UI state on it resets (BI-65). An open "Past periods" section is the
// observable proof - it is collapsed by default, so a remount closes it.
test("an open Past periods section stays open after marking a bill paid", async ({ page }) => {
  await page.goto("/");

  const pastToggle = page.getByRole("button", { name: "Past periods" });
  await pastToggle.click();
  await expect(pastToggle).toHaveAttribute("aria-expanded", "true");

  const streaming = page.locator("li.bill-row", { hasText: "Streaming" });
  await streaming.getByRole("button", { name: "Paid" }).click();
  await streaming.getByRole("button", { name: "Confirm paid date" }).click();

  // The action landed and the schedule refetched...
  await expect(streaming.locator(".bill-row__status-word")).toHaveText("PAID");
  // ...without resetting the Dashboard's UI state.
  await expect(pastToggle).toHaveAttribute("aria-expanded", "true");
});
