import { expect, test } from "@playwright/test";
import { expectNoA11yViolations } from "./helpers";

/**
 * Phase 0 smoke suite: proves the app serves, the token system applies, and
 * there are no baseline accessibility violations.
 */

test.describe("landing page", () => {
  test("renders and has a single h1", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Resumes that clear");
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
    expect(bg).not.toBe("rgba(0, 0, 0, 0)");
    expect(bg).not.toBe("rgb(255, 255, 255)");
  });

  test("main landmark exists and is targetable", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("main#main")).toBeVisible();
  });
});

test.describe("accessibility", () => {
  test("landing page has no WCAG A/AA violations", async ({ page }) => {
    await page.goto("/");
    await expectNoA11yViolations(page);
  });

  test("no WCAG violations in light theme", async ({ page }) => {
    await page.goto("/");
    // Use the real control, and confirm it applied, rather than setting the
    // attribute directly — that silently no-ops if the selector changes.
    await page.getByRole("radio", { name: "Light" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await expectNoA11yViolations(page);
  });
});
