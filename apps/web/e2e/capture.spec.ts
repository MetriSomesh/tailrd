import { test } from "@playwright/test";

/**
 * Screenshot capture for design review. Not an assertion suite.
 *
 * Captures viewport-sized frames at scroll anchors rather than one fullPage
 * image: fullPage resizes the viewport, which resets scroll-reveal transitions
 * and produces blank sections that do not reflect what users see.
 *
 * Run: npx playwright test capture
 */

const pages = [
  { path: "/", name: "landing", frames: 4 },
  { path: "/pricing", name: "pricing", frames: 3 },
  { path: "/dashboard", name: "dashboard", frames: 2 },
  { path: "/tailor", name: "tailor", frames: 2 },
  { path: "/runs", name: "runs", frames: 1 },
  { path: "/billing", name: "billing", frames: 2 },
];

for (const { path, name, frames } of pages) {
  test(`capture ${name}`, async ({ page }, testInfo) => {
    await page.goto(path, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(500);

    for (let i = 0; i < frames; i++) {
      // Scroll one viewport at a time and let the reveal finish before capturing.
      await page.evaluate((step) => window.scrollTo(0, step * window.innerHeight * 0.9), i);
      await page.waitForTimeout(900);
      await page.screenshot({
        path: `.playwright/shots/${name}-${i + 1}-${testInfo.project.name}.png`,
      });
    }
  });
}
