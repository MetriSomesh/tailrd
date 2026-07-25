import { expect, test } from "@playwright/test";
import { expectNoA11yViolations } from "./helpers";

test.describe("signup page", () => {
  test("renders the form (no 404)", async ({ page }) => {
    const res = await page.goto("/signup");
    expect(res?.status()).toBeLessThan(400);
    await expect(page.getByRole("heading", { name: /create your account/i })).toBeVisible();
    await expect(page.getByLabel("Name")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: /create account/i })).toBeVisible();
  });

  test("offers Google sign-up", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByRole("link", { name: /sign up with google/i })).toBeVisible();
  });

  test("links to login", async ({ page }) => {
    await page.goto("/signup");
    await page.getByRole("link", { name: /^sign in$/i }).click();
    await expect(page).toHaveURL(/\/login/);
  });

  test("passes WCAG audit", async ({ page }) => {
    await page.goto("/signup");
    await expectNoA11yViolations(page);
  });
});

test.describe("login page", () => {
  test("renders the form (no 404)", async ({ page }) => {
    const res = await page.goto("/login");
    expect(res?.status()).toBeLessThan(400);
    await expect(page.getByRole("heading", { name: /welcome back/i })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByRole("button", { name: /^sign in$/i })).toBeVisible();
  });

  test("has a forgot-password link that resolves", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: /forgot password/i }).click();
    await expect(page).toHaveURL(/\/forgot-password/);
    await expect(page.getByRole("heading", { name: /reset password/i })).toBeVisible();
  });

  test("passes WCAG audit", async ({ page }) => {
    await page.goto("/login");
    await expectNoA11yViolations(page);
  });
});

test.describe("marketing to auth flow", () => {
  test("Get started reaches signup, not a 404", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /get started/i }).first().click();
    await expect(page).toHaveURL(/\/signup/);
    await expect(page.getByRole("heading", { name: /create your account/i })).toBeVisible();
  });

  test("hero Start for free reaches signup", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /start for free/i }).click();
    await expect(page).toHaveURL(/\/signup/);
  });
});

test.describe("onboarding", () => {
  test("renders the welcome steps (no 404)", async ({ page }) => {
    const res = await page.goto("/onboarding");
    expect(res?.status()).toBeLessThan(400);
    await expect(page.getByRole("heading", { name: /build your base resume/i })).toBeVisible();
  });

  test("passes WCAG audit", async ({ page }) => {
    await page.goto("/onboarding");
    await expectNoA11yViolations(page);
  });
});

test.describe("display font", () => {
  test("headings use the Space Grotesk display variable, not a serif", async ({ page }) => {
    await page.goto("/");
    const family = await page
      .getByRole("heading", { level: 1 })
      .evaluate((el) => getComputedStyle(el).fontFamily.toLowerCase());
    expect(family).toContain("space grotesk");
    expect(family).not.toContain("instrument");
    expect(family).not.toContain("serif");
  });
});
