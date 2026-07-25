/**
 * Single source of truth for site-wide constants.
 * Keeps brand copy out of components so a rename is one edit.
 */

export const SITE = {
  name: "Tailrd",
  tagline: "Resumes that clear the filter",
  description:
    "Tailrd rewrites your resume for a specific job description, scores it against real ATS criteria, and shows you exactly which requirements you have not covered yet.",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  locale: "en_IN",
  supportEmail: "support@tailrd.app",
  legalEntity: "Tailrd",
} as const;

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Pricing, in paise, mirrored from the backend config. */
export const PRICING = {
  free: {
    id: "free",
    name: "Free",
    pricePaise: 0,
    cadence: null,
    resumesLabel: "3 resumes per month",
    fairUse: "3 per day",
  },
  perResume: {
    id: "per_resume",
    name: "Per resume",
    pricePaise: 2900,
    cadence: "one-time",
    resumesLabel: "1 resume credit",
    fairUse: "10 per day",
  },
  weekly: {
    id: "weekly",
    name: "Weekly",
    pricePaise: 14900,
    cadence: "week",
    resumesLabel: "Unlimited for 7 days",
    fairUse: "15 per day, 60 per week",
  },
  monthly: {
    id: "monthly",
    name: "Monthly",
    pricePaise: 34900,
    cadence: "month",
    resumesLabel: "Unlimited for 30 days",
    fairUse: "15 per day, 150 per month",
  },
} as const;

export type PlanId = keyof typeof PRICING;

/** Format paise as Indian Rupees without trailing decimals for whole amounts. */
export function formatPaise(paise: number): string {
  const rupees = paise / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: rupees % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(rupees);
}
