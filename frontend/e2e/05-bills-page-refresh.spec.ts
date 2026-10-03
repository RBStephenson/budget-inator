import { test, expect } from "@playwright/test";

// Runs after 04-, against the pay schedule and bills that 04's import
// restored. A one-time bill due today always lands in the current period
// (spec 02 anchors a monthly schedule two weeks back), which sidesteps the
// Quick Add due-day cap of 28.
//
// Each test starts on /bills and reaches the Dashboard through the in-app
// link, never page.goto("/"): a fresh page load remounts ScheduleProvider and
// refetches regardless, so only client-side navigation can show whether the
// Bills page refreshed the shared schedule (BI-63, same class as BI-54/57).
test.describe.serial("bills page changes reach the dashboard without a reload", () => {
  test("a bill added on the Bills page shows on the Dashboard", async ({ page }) => {
    await page.goto("/bills");

    await page.getByLabel("Bill name").fill("Gym");
    await page.getByLabel("Amount").fill("30.00");
    await page.getByLabel("Recurrence").selectOption("one_time");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await expect(page.getByRole("button", { name: "Deactivate Gym" })).toBeVisible();

    await page.getByRole("link", { name: "← Dashboard" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator("li.bill-row", { hasText: "Gym" })).toBeVisible();
  });

  test("a bill deactivated on the Bills page leaves the Dashboard", async ({ page }) => {
    await page.goto("/bills");

    await page.getByRole("button", { name: "Deactivate Gym" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Deactivate" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible();

    await page.getByRole("link", { name: "← Dashboard" }).click();
    await expect(page).toHaveURL(/\/$/);
    // Positive anchor first, so the absence check below runs against a
    // rendered schedule rather than a still-loading page.
    await expect(page.locator("li.bill-row", { hasText: "Internet" })).toBeVisible();
    await expect(page.locator("li.bill-row", { hasText: "Gym" })).toHaveCount(0);
  });
});
