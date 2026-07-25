import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Phase 0 smoke suite: proves the app serves, the token system applies, and
 * there are no baseline accessibility violations.
 */

test.describe("landing page", () => {
  test("renders and has a single h1", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Tailrd");
  });

  test("has a descriptive title and meta description", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Tailrd/);
    const description = await page
      .locator('meta[name="description"]')
      .getAttribute("content");
    expect(description).toBeTruthy();
    expect((description ?? "").length).toBeGreaterThan(50);
  });

  test("applies the dark theme before paint", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("design tokens resolve to real values", async ({ page }) => {
    await page.goto("/");
    const bg = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor,
    );
    // Must not be the browser default (transparent / white).
    expect(bg).not.toBe("rgba(0, 0, 0, 0)");
    expect(bg).not.toBe("rgb(255, 255, 255)");
  });

  test("skip link is reachable by keyboard", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus-visible");
    await expect(focused).toContainText(/skip to content/i);
  });

  test("main landmark exists and is targetable", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("main#main")).toBeVisible();
  });
});

test.describe("accessibility", () => {
  test("landing page has no WCAG A/AA violations", async ({ page }) => {
    await page.goto("/");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    // Print a readable summary before asserting, so CI logs are actionable.
    if (results.violations.length > 0) {
      console.error(
        JSON.stringify(
          results.violations.map((v) => ({
            id: v.id,
            impact: v.impact,
            help: v.help,
            nodes: v.nodes.map((n) => n.target).slice(0, 3),
          })),
          null,
          2,
        ),
      );
    }
    expect(results.violations).toEqual([]);
  });

  test("no WCAG violations in light theme", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => {
      document.documentElement.setAttribute("data-theme", "light");
    });
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});
