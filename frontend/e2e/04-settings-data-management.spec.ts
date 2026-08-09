import { test, expect } from "@playwright/test";

// Runs last (04-): deletes all data, which is destructive to whatever state
// earlier specs built up. Continues from the pay schedule + bills left by
// 02-onboarding-and-bills.spec.ts and 03-edit-and-skip-bill.spec.ts.
test.describe.serial("settings data management: export, delete, import", () => {
  let exportedBackup: Buffer;

  test("exports a backup", async ({ page }) => {
    await page.goto("/settings");

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export backup" }).click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toMatch(/^budget-inator-backup-\d{4}-\d{2}-\d{2}\.json$/);

    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream!) chunks.push(chunk as Buffer);
    exportedBackup = Buffer.concat(chunks);

    const parsed = JSON.parse(exportedBackup.toString("utf-8"));
    expect(parsed).toBeTruthy();
  });

  test("delete gate stays closed until cancelled", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("button", { name: "Save changes" })).toBeVisible();

    await page.getByRole("button", { name: "Delete all data" }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Delete all data?")).toBeVisible();
    const confirmBtn = dialog.getByRole("button", { name: "Delete everything" });
    await expect(confirmBtn).toBeDisabled();

    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(dialog).not.toBeVisible();

    // Cancelling did nothing — data is still intact.
    await expect(page.getByRole("button", { name: "Save changes" })).toBeVisible();
  });

  test("deletes all data and the dashboard reflects it via client-side nav", async ({ page }) => {
    await page.goto("/settings");

    await page.getByRole("button", { name: "Delete all data" }).click();
    const dialog = page.getByRole("dialog");
    const confirmBtn = dialog.getByRole("button", { name: "Delete everything" });

    await dialog.getByLabel("Type DELETE to confirm").fill("DELETE");
    await expect(confirmBtn).toBeEnabled();
    await confirmBtn.click();

    await expect(dialog).not.toBeVisible();
    // Settings falls back to the first-time-setup create form.
    await expect(
      page.getByRole("button", { name: "Save and go to dashboard" })
    ).toBeVisible();

    // Same page/session, no reload — client-side nav via the in-app link,
    // not page.goto() (a fresh page load would remount ScheduleContext from
    // scratch regardless of whether the app itself refetches, so it
    // wouldn't actually test this).
    await page.getByRole("link", { name: "← Dashboard" }).click();
    await expect(page).toHaveURL(/\/$/);

    await expect(
      page.getByRole("heading", { name: "Welcome to Budget-inator" })
    ).toBeVisible();
  });

  test("imports the backup to restore data", async ({ page }) => {
    await page.goto("/settings");
    await expect(
      page.getByRole("button", { name: "Save and go to dashboard" })
    ).toBeVisible();

    await page.getByLabel("Import backup file").setInputFiles({
      name: "budget-inator-backup.json",
      mimeType: "application/json",
      buffer: exportedBackup,
    });

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Import backup?")).toBeVisible();
    await dialog.getByRole("button", { name: "Import and overwrite" }).click();

    // Restored — the edit form (pre-populated, "Save changes") is back.
    await expect(page.getByRole("button", { name: "Save changes" })).toBeVisible();
  });
});
