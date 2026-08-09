import { test, expect } from "@playwright/test";

// Runs against the isolated E2E stack (docker-compose.e2e.yml) with a fresh,
// empty database — no seeded schedule. That's deliberate: the onboarding
// heading only renders once the frontend has successfully round-tripped a
// real "no-schedule" response from the real backend, so seeing it proves the
// harness is actually driving a browser against the live stack end-to-end,
// not a mock.
test("dashboard loads and reflects a real no-schedule response from the backend", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Welcome to Budget-inator" })
  ).toBeVisible();
});
