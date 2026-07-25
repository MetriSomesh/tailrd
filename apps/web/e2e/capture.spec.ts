import { test } from "@playwright/test";

/**
 * Screenshot capture for design review. Not an assertion suite.
 * Captures viewport frames at scroll anchors (fullPage resets reveal state).
 */
const pages = [
  { path: "/", name: "landing", frames: 4 },
  { path: "/signup", name: "signup", frames: 1 },
  { path: "/login", name: "login", frames: 1 },
  { path: "/pricing", name: "pricing", frames: 2 },
  { path: "/dashboard", name: "dashboard", frames: 2 },
  { path: "/tailor", name: "tailor", frames: 1 },
  { path: "/onboarding", name: "onboarding", frames: 1 },
];

for (const { path, name, frames } of pages) {
  test(`capture ${name}`, async ({ page }, testInfo) => {
    await page.goto(path, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(500);
    for (let i = 0; i < frames; i++) {
      await page.evaluate((step) => window.scrollTo(0, step * window.innerHeight * 0.9), i);
      await page.waitForTimeout(850);
      await page.screenshot({ path: `.playwright/shots/${name}-${i + 1}-${testInfo.project.name}.png` });
    }
  });
}
