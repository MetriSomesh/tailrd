import AxeBuilder from "@axe-core/playwright";
import { type Page, type Route, expect } from "@playwright/test";

/**
 * Intercepts the same-origin API proxy (`/api/backend/*`) so app-page tests can
 * render against fixtures without a live backend. Every app route is auth-gated
 * (GET /auth/me) and data-driven (usage, runs), so this stands those in.
 */
export interface MockBackendData {
  me?: Record<string, unknown> | null; // null → simulate 401 (signed out)
  usage?: Record<string, unknown>;
  runs?: Record<string, unknown>[];
  runDetails?: Record<string, Record<string, unknown>>;
}

const DEFAULT_ME = {
  id: "u_test",
  email: "test@tailrd.app",
  name: "Test User",
  avatar_url: null,
  auth_provider: "password",
  email_verified: true,
  created_at: "2026-01-01T00:00:00Z",
};

const DEFAULT_USAGE = {
  has_subscription: false,
  subscription_plan: null,
  subscription_ends: null,
  credit_balance: 0,
  free_used: 1,
  free_limit: 3,
  free_remaining: 2,
  period: "2026-07",
};

const DEFAULT_RUNS = [
  {
    id: "r1",
    status: "succeeded",
    jd_label: "AI Engineer at Lexi",
    company: "Lexi",
    role: "AI Engineer",
    overall_score: 84.5,
    created_at: "2026-07-25T10:00:00Z",
    finished_at: "2026-07-25T10:01:00Z",
  },
  {
    id: "r2",
    status: "running",
    jd_label: "Backend Engineer at Stripe",
    company: "Stripe",
    role: "Backend Engineer",
    overall_score: null,
    created_at: "2026-07-25T09:00:00Z",
    finished_at: null,
  },
  {
    id: "r3",
    status: "succeeded",
    jd_label: "Full Stack at Vercel",
    company: "Vercel",
    role: "Full Stack",
    overall_score: 71.2,
    created_at: "2026-07-24T09:00:00Z",
    finished_at: "2026-07-24T09:01:00Z",
  },
];

const DEFAULT_DETAILS: Record<string, Record<string, unknown>> = {
  r1: {
    ...DEFAULT_RUNS[0],
    jd_text: "…",
    tailored_json: null,
    parsability_json: null,
    iterations: 1,
    error_code: null,
    error_message: null,
    docx_storage_key: "runs/r1/resume.docx",
    score_json: {
      overall_score: 84.5,
      keyword_match_pct: 56,
      skills_match_pct: 100,
      term_overlap_pct: 100,
      experience_relevance_pct: 100,
      matched_keywords: [],
      missing_keywords: [],
      skills_matched: ["LLM agents", "Retrieval", "Backend APIs", "Evals"],
      skills_missing: ["Kubernetes"],
      responsibilities_covered: [],
      responsibilities_uncovered: [],
    },
  },
};

export async function mockBackend(page: Page, data: MockBackendData = {}): Promise<void> {
  const me = data.me === undefined ? DEFAULT_ME : data.me;
  const usage = data.usage ?? DEFAULT_USAGE;
  const runs = data.runs ?? DEFAULT_RUNS;
  const details = data.runDetails ?? DEFAULT_DETAILS;

  await page.route("**/api/backend/**", async (route: Route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/backend", "");

    if (path === "/auth/me") {
      if (me === null) {
        return route.fulfill({
          status: 401,
          json: { code: "not_authenticated", title: "Unauthorized", detail: "Not authenticated.", status: 401 },
        });
      }
      return route.fulfill({ json: me });
    }
    if (path === "/billing/usage") return route.fulfill({ json: usage });
    if (path === "/runs") return route.fulfill({ json: runs });

    if (path === "/profile") {
      return route.fulfill({
        json: {
          id: "p_test", full_name: null, phone: null, email: null, location: null,
          linkedin_url: null, github_url: null, hook_line: null, allow_ai_projects: false,
          onboarding_step: 0, is_complete: false,
          educations: [], experiences: [], projects: [], skills: [],
        },
      });
    }

    const runMatch = path.match(/^\/runs\/([^/]+)$/);
    if (runMatch) {
      const detail = details[runMatch[1]] ?? runs.find((r) => r.id === runMatch[1]) ?? {};
      return route.fulfill({ json: detail });
    }

    return route.fulfill({
      status: 404,
      json: { code: "not_found", title: "Not found", detail: "Not found.", status: 404 },
    });
  });
}

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
