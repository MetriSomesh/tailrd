import { PlanCard, type PlanCardProps } from "@/components/marketing/plan-card";
import { Reveal } from "@/components/motion/reveal";
import { PricingFaqJsonLd } from "@/components/seo/json-ld";
import { PRICING, SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing",
  description: `${SITE.name} pricing: three free resumes every month, then ₹29 per resume or unlimited from ₹149 a week.`,
};

const plans: PlanCardProps[] = [
  {
    name: PRICING.free.name,
    pricePaise: 0,
    cadence: null,
    note: "Resets on the 1st",
    features: ["3 resumes per month", "Full ATS scoring", "Gap report", "DOCX download"],
    cta: "Start free",
    href: "/signup",
  },
  {
    name: PRICING.perResume.name,
    pricePaise: PRICING.perResume.pricePaise,
    cadence: "one-time",
    note: "Credits never expire",
    features: ["1 resume credit", "Everything in Free", "No subscription", "Buy as needed"],
    cta: "Buy a credit",
    href: "/signup",
  },
  {
    name: PRICING.weekly.name,
    pricePaise: PRICING.weekly.pricePaise,
    cadence: "week",
    note: "Fair use: 15 a day, 60 a week",
    features: ["Unlimited for 7 days", "Everything in Free", "Cancel anytime", "For an active search"],
    cta: "Go weekly",
    href: "/signup",
    featured: true,
  },
  {
    name: PRICING.monthly.name,
    pricePaise: PRICING.monthly.pricePaise,
    cadence: "month",
    note: "Fair use: 15 a day, 150 a month",
    features: ["Unlimited for 30 days", "Everything in Free", "Best per-resume value", "Cancel anytime"],
    cta: "Go monthly",
    href: "/signup",
  },
];

const faqs = [
  {
    q: "What counts as one resume?",
    a: "One tailoring run against one job description. Re-running the same posting counts again, because the model regenerates the content.",
  },
  {
    q: "Do credits expire?",
    a: "No. A credit bought today works a year from now.",
  },
  {
    q: "What if a run fails?",
    a: "If it fails on our side, the credit or free-tier count is refunded automatically. You do not need to ask.",
  },
  {
    q: "Why is unlimited capped?",
    a: "A documented ceiling keeps the queue fast for everyone and stops abuse. Fifteen a day is far above what a real search needs.",
  },
];

export default function PricingPage() {
  return (
    <>
      <PricingFaqJsonLd />

      <section className="relative overflow-hidden border-b border-border-strong">
        <div aria-hidden="true" className="bg-ruled absolute inset-0 -z-10 opacity-70" />

        <div className="container-page py-20 lg:py-24">
          <Reveal className="max-w-2xl">
            <p className="eyebrow flex items-center gap-2">
              <span className="inline-block h-px w-6 bg-accent" />
              Pricing
            </p>
            <h1 className="type-display mt-5 text-fluid-h2 text-balance text-fg">
              Free to start. Cheap to continue.
            </h1>
            <p className="mt-5 max-w-lg text-pretty text-fg-secondary">
              Three resumes a month cost nothing. Beyond that, pay per resume or go unlimited
              for as long as your search lasts.
            </p>
          </Reveal>

          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {plans.map((plan, i) => (
              <Reveal key={plan.name} delay={i * 70} className="flex">
                <PlanCard {...plan} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section>
        <div className="container-page py-20 lg:py-24">
          <Reveal>
            <p className="eyebrow">Questions</p>
            <h2 className="type-display mt-3 text-fluid-h2 text-fg">Before you pay</h2>
          </Reveal>

          <div className="mt-12 grid gap-x-12 gap-y-9 sm:grid-cols-2">
            {faqs.map((f, i) => (
              <Reveal key={f.q} delay={i * 60}>
                <h3 className="text-base font-medium text-fg">{f.q}</h3>
                <p className="mt-2 text-sm leading-relaxed text-fg-secondary">{f.a}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
