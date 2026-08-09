import { defineConfig } from "@playwright/test";

// Targets the isolated E2E Docker stack (docker-compose.e2e.yml), never the
// live dev stack — see that file for why. Start the stack yourself before
// running this suite; it does not manage the stack's lifecycle.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:8091",
    trace: "on-first-retry",
  },
});
