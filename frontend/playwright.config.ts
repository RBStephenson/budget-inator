import { defineConfig } from "@playwright/test";

// Targets the isolated E2E Docker stack (docker-compose.e2e.yml), never the
// live dev stack — see that file for why. Start the stack yourself before
// running this suite; it does not manage the stack's lifecycle.
export default defineConfig({
  testDir: "./e2e",
  // All specs share one persistent DB for the run (docker-compose.e2e.yml
  // isn't reset between files) — run fully serial so state built up in one
  // file (e.g. onboarding) can't race a test in another file that assumes
  // a clean slate (e.g. 01-dashboard.spec.ts's no-schedule check). Playwright
  // runs files in alphabetical order, so specs are numbered (NN-name.spec.ts)
  // to make the required run order explicit rather than accidental.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:8091",
    trace: "on-first-retry",
  },
});
