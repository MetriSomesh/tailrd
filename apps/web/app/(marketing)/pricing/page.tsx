import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PRICING, SITE, formatPaise } from "@/lib/site";
import { Check } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing",
  description: `${SITE.name} pricing: 3 free resumes per month, then ₹29 per resume or unlimited plans from ₹149/week.`,
};

const plans = [
  {
    ...PRICING.free,
    features: ["3 resumes per month", "Full ATS scoring", "DOCX download", "No credit card required"],
    cta: "Get started free",
    href: "/signup",
    highlighted: false,
  },
  {
    ...PRICING.perResume,
    features: ["1 resume credit", "Never expires", "Use when you need it", "No commitment"],
    cta: "Buy credit",
    href: "/signup",
    highlighted: false,
  },
  {
    ...PRICING.weekly,
    features: ["Unlimited for 7 days", "15/day fair use", "Cancel anytime", "Ideal for active job search"],
    cta: "Start weekly",
    href: "/signup",
    highlighted: true,
  },
  {
    ...PRICING.monthly,
    features: ["Unlimited for 30 days", "15/day fair use", "Best per-resume value", "Priority support"],
    cta: "Start monthly",
    href: "/signup",
    highlighted: false,
  },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-20 lg:py-28">
      <div className="text-center">
        <p className="eyebrow mb-4">Pricing</p>
        <h1 className="display text-4xl text-fg sm:text-5xl">Simple, honest pricing</h1>
        <p className="mx-auto mt-5 max-w-lg text-lg text-fg-secondary">
          Start free. Pay only when you need more. No subscriptions required.
        </p>
      </div>

      <div className="mt-16 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map((plan) => (
          <Card
            key={plan.id}
            className={`flex flex-col justify-between ${plan.highlighted ? "ring-2 ring-accent shadow-lg" : ""}`}
          >
            <div>
              <CardHeader>
                <CardTitle>{plan.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-fg">
                  {plan.pricePaise === 0 ? "Free" : formatPaise(plan.pricePaise)}
                </p>
                <p className="mt-0.5 text-xs text-fg-quaternary">
                  {plan.cadence ? (plan.cadence === "one-time" ? "one-time" : `per ${plan.cadence}`) : "forever"}
                </p>
                <ul className="mt-5 space-y-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-fg-secondary">
                      <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-success" />
                      {f}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </div>
            <div className="mt-6 px-5 pb-5">
              <a href={plan.href}>
                <Button
                  variant={plan.highlighted ? "primary" : "secondary"}
                  size="md"
                  className="w-full"
                >
                  {plan.cta}
                </Button>
              </a>
            </div>
          </Card>
        ))}
      </div>

      {/* Fair use note */}
      <p className="mx-auto mt-10 max-w-xl text-center text-xs text-fg-quaternary">
        &ldquo;Unlimited&rdquo; plans are subject to documented fair-use limits (15 resumes/day, 60/week or 150/month).
        This prevents abuse and keeps the service fast for everyone.
      </p>
    </div>
  );
}
