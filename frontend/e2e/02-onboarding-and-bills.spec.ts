import { test, expect } from "@playwright/test";

// Serial: each test builds on state left behind by the previous one, in the
// same ephemeral DB (docker-compose.e2e.yml). This mirrors a real new user's
// first session — set up a pay schedule, add a bill, mark it paid — rather
// than re-seeding via API for each step.
test.describe.serial("new-user journey: onboarding, add bill, mark paid", () => {
  test("completes pay-schedule onboarding", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Welcome to Budget-inator" })
    ).toBeVisible();

    await page.getByRole("link", { name: "Set up pay schedule →" }).click();
    await expect(page).toHaveURL(/\/settings$/);

    await page.locator("#ps-salary").fill("2000.00");
    await page.locator("#ps-frequency").selectOption("monthly");

    const anchorDate = new Date();
    anchorDate.setDate(anchorDate.getDate() - 14);
    await page.locator("#ps-start-date").fill(anchorDate.toISOString().slice(0, 10));

    await page.locator("#ps-balance").fill("500.00");
    await page.getByRole("button", { name: "Save and go to dashboard" }).click();
    await expect(page).toHaveURL(/\/$/);

    await expect(
      page.getByRole("heading", { name: "Welcome to Budget-inator" })
    ).not.toBeVisible();
  });

  test("adds a bill", async ({ page }) => {
    await page.goto("/");

    await page.getByLabel("Bill name").fill("Internet");
    await page.getByLabel("Amount").fill("75.00");
    await page.getByRole("button", { name: "Add" }).click();

    await expect(page.locator("li.bill-row", { hasText: "Internet" })).toBeVisible();
  });

  test("marks the bill paid", async ({ page }) => {
    await page.goto("/");

    const billRow = page.locator("li.bill-row", { hasText: "Internet" });
    await expect(billRow).toBeVisible();
    await expect(billRow.locator(".bill-row__status-word")).toHaveText("DUE SOON");

    await billRow.getByRole("button", { name: "Paid" }).click();
    await billRow.getByRole("button", { name: "Confirm paid date" }).click();

    await expect(billRow.locator(".bill-row__status-word")).toHaveText("PAID");
    await expect(billRow.getByRole("button", { name: "Undo" })).toBeVisible();
  });
});
