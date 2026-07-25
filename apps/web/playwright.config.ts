import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config.
 *
 * Phase 7 runs E2E + accessibility here.
 * Phase 10 adds visual regression baselines (deliberately last, once the
 * design is real — baselines against a placeholder are worthless).
 */
export default defineConfig({
  testDir: "./e2e",
  outputDir: "./.playwright/results",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  timeout: 30_000,
  expect: {
    timeout: 5_000,
    toHaveScreenshot: {
      // Tolerate sub-pixel font rendering differences across platforms.
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
      scale: "css",
    },
  },
  reporter: process.env.CI
    ? [["github"], ["html", { outputFolder: "./.playwright/report", open: "never" }]]
    : [["list"], ["html", { outputFolder: "./.playwright/report", open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // Deterministic rendering for visual comparisons.
    colorScheme: "dark",
    timezoneId: "Asia/Kolkata",
    locale: "en-IN",
  },
  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "mobile-chromium",
      use: { ...devices["Pixel 7"] },
    },
  ],
  webServer: {
    command: "npm run start",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: "ignore",
    stderr: "pipe",
  },
});
