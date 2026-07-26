import { expect, test } from "@playwright/test";
import { mockBackend } from "./helpers";

/** Light-theme capture, to verify it is a real design and not an inversion. */
const pages = [
  { path: "/", name: "landing" },
  { path: "/dashboard", name: "dashboard" },
  { path: "/pricing", name: "pricing" },
];

for (const { path, name } of pages) {
  test(`capture light ${name}`, async ({ page }, testInfo) => {
    // Stand in the backend so auth-gated pages render their real content.
    await mockBackend(page);
    await page.goto(path, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("radio", { name: "System" })).toBeChecked();
    await page.getByRole("radio", { name: "Light" }).click();
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(700);
    await page.screenshot({
      path: `.playwright/shots/light-${name}-${testInfo.project.name}.png`,
    });
  });
}
