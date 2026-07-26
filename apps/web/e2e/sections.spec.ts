import { expect, test } from "@playwright/test";

/**
 * Asserts every landing section actually renders its content.
 * Guards against the scroll-reveal trapping content at opacity 0.
 */
test.describe("landing sections render", () => {
  test("all section headings are present in the DOM", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Resumes that clear the filter/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Most checkers grade against a template/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Three steps, about a minute/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Stop guessing what the filter wants/i })).toBeVisible();
  });

  test("revealed sections reach full opacity after scrolling", async ({ page }) => {
    await page.goto("/");
    const cta = page.getByRole("heading", { name: /Stop guessing what the filter wants/i });
    await cta.scrollIntoViewIfNeeded();
    // The reveal wrapper must end at opacity 1.
    await expect
      .poll(async () =>
        cta.evaluate((el) => {
          const wrapper = el.closest("[data-reveal]");
          return wrapper ? getComputedStyle(wrapper).opacity : "1";
        }),
      )
      .toBe("1");
  });

  test("content is visible with JavaScript disabled", async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false });
    const page = await context.newPage();
    await page.goto("/");
    // Without JS, html.js is never set, so the reveal hidden state must not apply.
    const opacity = await page
      .getByRole("heading", { name: /Stop guessing what the filter wants/i })
      .evaluate((el) => {
        const wrapper = el.closest("[data-reveal]");
        return wrapper ? getComputedStyle(wrapper).opacity : "1";
      });
    expect(opacity).toBe("1");
    await context.close();
  });

  test("theme toggle switches to light and back", async ({ page }) => {
    await page.goto("/");
    const html = page.locator("html");
    // Wait for hydration before interacting (default "System" becomes checked).
    await expect(page.getByRole("radio", { name: "System" })).toBeChecked();
    await page.getByRole("radio", { name: "Light" }).click();
    await expect(html).toHaveAttribute("data-theme", "light");
    await page.getByRole("radio", { name: "Dark" }).click();
    await expect(html).toHaveAttribute("data-theme", "dark");
  });

  test("theme choice survives a reload", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("radio", { name: "System" })).toBeChecked();
    await page.getByRole("radio", { name: "Light" }).click();
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  });
});
