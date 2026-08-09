import { test, expect } from "@playwright/test";

// Serial, continuing directly from the pay schedule set up in
// onboarding-and-bills.spec.ts (same ephemeral DB for the whole run) —
// no need to re-onboard, just add a fresh bill to exercise skip/undo/edit
// without disturbing the "Internet" bill already marked paid there.
test.describe.serial("bill lifecycle: skip, undo, edit", () => {
  test("adds a second bill to skip/edit", async ({ page }) => {
    await page.goto("/");

    await page.getByLabel("Bill name").fill("Streaming");
    await page.getByLabel("Amount").fill("15.00");
    await page.getByRole("button", { name: "Add" }).click();

    await expect(page.locator("li.bill-row", { hasText: "Streaming" })).toBeVisible();
  });

  test("skips the bill", async ({ page }) => {
    await page.goto("/");

    const billRow = page.locator("li.bill-row", { hasText: "Streaming" });
    await expect(billRow.locator(".bill-row__status-word")).toHaveText("DUE SOON");

    await billRow.getByRole("button", { name: "Skip" }).click();

    await expect(billRow.locator(".bill-row__status-word")).toHaveText("SKIPPED");
    await expect(billRow.getByRole("button", { name: "Undo" })).toBeVisible();
  });

  test("undoes the skip", async ({ page }) => {
    await page.goto("/");

    const billRow = page.locator("li.bill-row", { hasText: "Streaming" });
    await expect(billRow.locator(".bill-row__status-word")).toHaveText("SKIPPED");

    await billRow.getByRole("button", { name: "Undo" }).click();

    await expect(billRow.locator(".bill-row__status-word")).toHaveText("DUE SOON");
    await expect(billRow.getByRole("button", { name: "Skip" })).toBeVisible();
  });

  test("edits the bill's amount", async ({ page }) => {
    await page.goto("/");

    const billRow = page.locator("li.bill-row", { hasText: "Streaming" });
    await billRow.getByRole("button", { name: "Edit bill Streaming" }).click();

    const modal = page.getByRole("dialog", { name: "Edit bill" });
    await expect(modal).toBeVisible();
    await expect(modal.locator("#bf-amount")).toHaveValue("15");

    await modal.locator("#bf-amount").fill("18.50");
    await modal.getByRole("button", { name: "Save changes" }).click();

    await expect(modal).not.toBeVisible();
    await expect(billRow.locator(".bill-row__amount")).toContainText("18.50");
  });
});
