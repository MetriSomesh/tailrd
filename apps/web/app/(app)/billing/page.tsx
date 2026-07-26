import { Reveal } from "@/components/motion/reveal";
import { Button, ButtonLink } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { PRICING, formatPaise } from "@/lib/site";
import { Check } from "lucide-react";

const usage = { freeUsed: 1, freeLimit: 3, credits: 0, hasSubscription: false };

const options = [
  {
    id: "per",
    name: PRICING.perResume.name,
    pricePaise: PRICING.perResume.pricePaise,
    cadence: "once",
    features: ["1 resume credit", "Never expires"],
    cta: "Buy credit",
  },
  {
    id: "weekly",
    name: PRICING.weekly.name,
    pricePaise: PRICING.weekly.pricePaise,
    cadence: "week",
    features: ["Unlimited 7 days", "15 a day fair use"],
    cta: "Subscribe",
    featured: true,
  },
  {
    id: "monthly",
    name: PRICING.monthly.name,
    pricePaise: PRICING.monthly.pricePaise,
    cadence: "month",
    features: ["Unlimited 30 days", "Best value"],
    cta: "Subscribe",
  },
];

export default function BillingPage() {
  const pct = Math.round((usage.freeUsed / usage.freeLimit) * 100);

  return (
    <div className="space-y-8">
      <Reveal>
        <p className="eyebrow flex items-center gap-2">
          <span className="inline-block h-px w-6 bg-accent" />
          Account
        </p>
        <h1 className="type-display mt-3 text-3xl text-fg sm:text-4xl">Billing</h1>
        <p className="mt-2 font-mono text-2xs uppercase tracking-wide text-fg-quaternary">
          Your plan, usage and credits
        </p>
      </Reveal>

      {/* Current usage */}
      <Reveal delay={70}>
        <section className="rounded-md border border-border-default bg-surface-raised">
          <div className="grid grid-cols-2 divide-x divide-border-subtle border-b border-border-subtle">
            <div className="p-5">
              <p className="mono-label">Current plan</p>
              <p className="type-display mt-2 text-2xl text-fg">
                {usage.hasSubscription ? "Unlimited" : "Free"}
              </p>
            </div>
            <div className="p-5">
              <p className="mono-label">Credits</p>
              <p className="type-display mt-2 text-2xl tabular-nums text-fg">{usage.credits}</p>
            </div>
          </div>

          <div className="space-y-2 p-5">
            <div className="flex items-baseline justify-between gap-2">
              <span className="mono-label">Free resumes this month</span>
              <span className="font-mono text-2xs tabular-nums text-fg-secondary">
                {usage.freeUsed} / {usage.freeLimit}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-[1px] bg-surface-sunken"
              role="progressbar"
              aria-valuenow={usage.freeUsed}
              aria-valuemin={0}
              aria-valuemax={usage.freeLimit}
              aria-label="Free resume usage"
            >
              <div
                className="h-full bg-accent transition-[width] duration-slow"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="font-mono text-2xs text-fg-quaternary">
              {usage.freeLimit - usage.freeUsed} remaining · resets on the 1st
            </p>
          </div>
        </section>
      </Reveal>

      {/* Upgrade options */}
      <Reveal delay={140}>
        <section>
          <h2 className="mono-label">Add capacity</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {options.map((o) => (
              <div
                key={o.id}
                className={cn(
                  "flex flex-col rounded-md border bg-surface-raised",
                  o.featured ? "border-border-strong hard-shadow" : "border-border-default",
                )}
              >
                <div
                  className={cn(
                    "border-b px-4 py-2.5",
                    o.featured ? "border-border-strong bg-accent" : "border-border-subtle",
                  )}
                >
                  <span
                    className={cn(
                      "font-mono text-2xs uppercase tracking-widest",
                      o.featured ? "text-accent-contrast" : "text-fg-tertiary",
                    )}
                  >
                    {o.name}
                  </span>
                </div>
                <div className="flex flex-1 flex-col p-4">
                  <div className="flex items-baseline gap-1.5">
                    <span className="type-display text-2xl tabular-nums text-fg">
                      {formatPaise(o.pricePaise)}
                    </span>
                    <span className="font-mono text-2xs text-fg-quaternary">/ {o.cadence}</span>
                  </div>
                  <ul className="mt-4 flex-1 space-y-2">
                    {o.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-xs text-fg-secondary">
                        <Check
                          className={cn(
                            "mt-0.5 size-3 shrink-0",
                            o.featured ? "text-accent-text" : "text-fg-tertiary",
                          )}
                        />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button
                    variant={o.featured ? "primary" : "secondary"}
                    size="sm"
                    className="mt-5 w-full"
                  >
                    {o.cta}
                  </Button>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 font-mono text-2xs text-fg-quaternary">
            Full plan details on the{" "}
            <ButtonLink href="/pricing" variant="ghost" size="sm" className="h-auto px-1 py-0 underline">
              pricing page
            </ButtonLink>
            .
          </p>
        </section>
      </Reveal>
    </div>
  );
}
