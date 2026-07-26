import { expect, test } from "@playwright/test";
import { expectNoA11yViolations, mockBackend } from "./helpers";

// Every app route is auth-gated and data-driven, so stand in the backend.
test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

test.describe("dashboard", () => {
  test("renders the heading and the stat strip", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Dashboard");
    await expect(page.getByText("Free usage")).toBeVisible();
    await expect(page.getByText("never expire")).toBeVisible();
    await expect(page.getByText("Best score")).toBeVisible();
  });

  test("has a tailor CTA", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("link", { name: /tailor a resume/i })).toBeVisible();
  });

  test("shows the score gauge with the value from the latest run", async ({ page }) => {
    await page.goto("/dashboard");
    const gauge = page.locator("[role='meter']");
    await expect(gauge).toBeVisible();
    await expect(gauge).toHaveAttribute("aria-valuenow", "84.5");
  });

  test("shows requirement coverage chips from the run's score", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("Requirement coverage")).toBeVisible();
    await expect(page.getByText("Kubernetes")).toBeVisible();
  });

  test("shows an empty state when there are no runs", async ({ page }) => {
    await mockBackend(page, { runs: [] });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: /no runs yet/i })).toBeVisible();
  });

  test("passes WCAG audit", async ({ page }) => {
    await page.goto("/dashboard");
    await expectNoA11yViolations(page);
  });
});

test.describe("tailor page", () => {
  test("renders the form", async ({ page }) => {
    await page.goto("/tailor");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Tailor a resume");
    await expect(page.getByLabel(/job description/i)).toBeVisible();
  });

  test("submit is disabled until the JD is long enough", async ({ page }) => {
    await page.goto("/tailor");
    const submit = page.getByRole("button", { name: /tailor resume/i });
    await expect(submit).toBeDisabled();
    await page.getByLabel(/job description/i).fill("x".repeat(60));
    await expect(submit).toBeEnabled();
  });

  test("shows a live character counter", async ({ page }) => {
    await page.goto("/tailor");
    await expect(page.getByText(/50 more characters/i)).toBeVisible();
  });

  test("passes WCAG audit", async ({ page }) => {
    await page.goto("/tailor");
    await expectNoA11yViolations(page);
  });
});

test.describe("runs page", () => {
  test("renders the run list", async ({ page }) => {
    await page.goto("/runs");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Runs");
    await expect(page.getByText("Lexi")).toBeVisible();
    await expect(page.getByText("Stripe")).toBeVisible();
  });

  test("download is a link for finished runs, absent for unfinished", async ({ page }) => {
    await page.goto("/runs");
    await expect(page.getByRole("link", { name: /download resume for Lexi/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /download resume for Stripe/i })).toHaveCount(0);
  });

  test("passes WCAG audit", async ({ page }) => {
    await page.goto("/runs");
    await expectNoA11yViolations(page);
  });
});

test.describe("billing page", () => {
  test("renders plan options", async ({ page }) => {
    await page.goto("/billing");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Billing");
    await expect(page.getByText("Per resume")).toBeVisible();
    await expect(page.getByText("Weekly")).toBeVisible();
    await expect(page.getByText("Monthly")).toBeVisible();
  });

  test("shows a usage progress bar", async ({ page }) => {
    await page.goto("/billing");
    await expect(page.getByRole("progressbar", { name: /free resume usage/i })).toBeVisible();
  });

  test("passes WCAG audit", async ({ page }) => {
    await page.goto("/billing");
    await expectNoA11yViolations(page);
  });
});

test.describe("app navigation", () => {
  test("marks the current page in the nav", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.locator('header a[aria-current="page"]').first()).toContainText("Dashboard");
  });

  test("theme toggle is reachable in the app shell", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("radiogroup", { name: /colour theme/i })).toBeVisible();
  });

  test("redirects to login when signed out", async ({ page }) => {
    await mockBackend(page, { me: null });
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });
});
