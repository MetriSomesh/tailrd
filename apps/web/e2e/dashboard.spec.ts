import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.describe("dashboard", () => {
  test("renders the dashboard heading and stats", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Dashboard");
    // Stats cards should be visible
    await expect(page.getByText("Usage")).toBeVisible();
    await expect(page.getByText("available credits")).toBeVisible();
    await expect(page.getByText("Best Score")).toBeVisible();
  });

  test("has a tailor resume CTA button", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("button", { name: /tailor resume/i })).toBeVisible();
  });

  test("shows the score gauge", async ({ page }) => {
    await page.goto("/dashboard");
    const gauge = page.locator("[role='meter']");
    await expect(gauge).toBeVisible();
    await expect(gauge).toHaveAttribute("aria-valuenow", "73.6");
  });

  test("passes WCAG accessibility audit", async ({ page }) => {
    await page.goto("/dashboard");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});

test.describe("tailor page", () => {
  test("renders the form with JD textarea", async ({ page }) => {
    await page.goto("/tailor");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Tailor a resume");
    await expect(page.getByLabel(/job description/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /tailor resume/i })).toBeVisible();
  });

  test("disables submit when JD is too short", async ({ page }) => {
    await page.goto("/tailor");
    const button = page.getByRole("button", { name: /tailor resume/i });
    await expect(button).toBeDisabled();
  });

  test("enables submit when JD is long enough", async ({ page }) => {
    await page.goto("/tailor");
    const textarea = page.getByLabel(/job description/i);
    await textarea.fill("x".repeat(60));
    const button = page.getByRole("button", { name: /tailor resume/i });
    await expect(button).toBeEnabled();
  });

  test("passes WCAG accessibility audit", async ({ page }) => {
    await page.goto("/tailor");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});

test.describe("runs page", () => {
  test("renders run history", async ({ page }) => {
    await page.goto("/runs");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Run History");
    // Should show mock runs
    await expect(page.getByText("Lexi")).toBeVisible();
    await expect(page.getByText("Stripe")).toBeVisible();
  });

  test("passes WCAG accessibility audit", async ({ page }) => {
    await page.goto("/runs");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});

test.describe("billing page", () => {
  test("shows pricing plans", async ({ page }) => {
    await page.goto("/billing");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Billing");
    // Check plan names exist (avoid locale-dependent currency formatting)
    await expect(page.getByText("Per resume")).toBeVisible();
    await expect(page.getByText("Weekly")).toBeVisible();
    await expect(page.getByText("Monthly")).toBeVisible();
  });

  test("passes WCAG accessibility audit", async ({ page }) => {
    await page.goto("/billing");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});

test.describe("navigation", () => {
  test("header nav links are present", async ({ page }) => {
    await page.goto("/dashboard");
    const nav = page.locator("header nav");
    await expect(nav.getByRole("link", { name: /dashboard/i })).toBeVisible();
    await expect(nav.getByRole("link", { name: /tailor/i })).toBeVisible();
    await expect(nav.getByRole("link", { name: /runs/i })).toBeVisible();
    await expect(nav.getByRole("link", { name: /billing/i })).toBeVisible();
  });
});
