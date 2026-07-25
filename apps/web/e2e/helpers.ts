import AxeBuilder from "@axe-core/playwright";
import { type Page, expect } from "@playwright/test";

/**
 * Waits until the page is visually settled before auditing.
 *
 * Scroll-reveal fades elements from opacity 0 to 1. If axe runs mid-transition
 * it samples a blended foreground colour and reports contrast failures that
 * vary between runs. This scrolls the whole page, waits for every reveal to be
 * marked `in`, then waits out the transition so colours are final.
 */
export async function settle(page: Page): Promise<void> {
  await page.evaluate(() => document.fonts.ready);

  // Walk the page so every IntersectionObserver fires.
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.75;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 90));
    }
    window.scrollTo(0, 0);
  });

  // No reveal may still be in the hidden state.
  await expect
    .poll(async () => page.locator('[data-reveal="out"]').count(), { timeout: 5000 })
    .toBe(0);

  // Let the longest transition (--duration-slow, 340ms) finish plus its delay.
  await page.waitForTimeout(700);
}

/** Runs an axe WCAG A/AA audit and prints readable violations before asserting. */
export async function expectNoA11yViolations(page: Page): Promise<void> {
  await settle(page);

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  if (results.violations.length > 0) {
    console.error(
      JSON.stringify(
        results.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          help: v.help,
          nodes: v.nodes.slice(0, 3).map((n) => ({ target: n.target, html: n.html })),
        })),
        null,
        2,
      ),
    );
  }
  expect(results.violations).toEqual([]);
}
