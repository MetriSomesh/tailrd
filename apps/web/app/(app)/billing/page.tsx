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
        <h1 className="type-display text-3xl text-fg sm:text-4xl">Billing</h1>
        <p className="mt-1.5 text-sm text-fg-tertiary">Your plan, usage and credits.</p>
      </Reveal>

      {/* Current usage with a real progress bar */}
      <Reveal delay={70}>
        <section className="hairline-top rounded-2xl bg-surface-raised p-6 ring-1 ring-border-subtle">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <h2 className="text-sm font-medium text-fg">Current plan</h2>
              <p className="mt-1 font-mono text-2xl font-semibold text-fg">
                {usage.hasSubscription ? "Unlimited" : "Free"}
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xs uppercase tracking-widest text-fg-tertiary">Credits</p>
              <p className="mt-1 font-mono text-2xl font-semibold tabular-nums text-fg">
                {usage.credits}
              </p>
            </div>
          </div>

          <div className="mt-6 space-y-2">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-xs text-fg-secondary">Free resumes this month</span>
              <span className="font-mono text-xs tabular-nums text-fg-secondary">
                {usage.freeUsed} / {usage.freeLimit}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-border-subtle"
              role="progressbar"
              aria-valuenow={usage.freeUsed}
              aria-valuemin={0}
              aria-valuemax={usage.freeLimit}
              aria-label="Free resume usage"
            >
              <div
                className="h-full rounded-full bg-accent transition-[width] duration-slow"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-2xs text-fg-quaternary">
              {usage.freeLimit - usage.freeUsed} remaining. Resets on the 1st.
            </p>
          </div>
        </section>
      </Reveal>

      {/* Upgrade options */}
      <Reveal delay={140}>
        <section>
          <h2 className="text-sm font-medium text-fg">Add capacity</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {options.map((o) => (
              <div
                key={o.id}
                className={cn(
                  "hairline-top flex flex-col rounded-2xl p-5",
                  o.featured
                    ? "bg-surface-raised ring-2 ring-accent"
                    : "bg-surface-raised/60 ring-1 ring-border-subtle",
                )}
              >
                <h3 className="text-sm font-medium text-fg">{o.name}</h3>
                <div className="mt-3 flex items-baseline gap-1.5">
                  <span className="font-mono text-2xl font-semibold tabular-nums text-fg">
                    {formatPaise(o.pricePaise)}
                  </span>
                  <span className="text-2xs text-fg-quaternary">/ {o.cadence}</span>
                </div>
                <ul className="mt-4 flex-1 space-y-2">
                  {o.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-xs text-fg-secondary">
                      <Check
                        className={cn(
                          "mt-0.5 size-3 shrink-0",
                          o.featured ? "text-accent" : "text-success",
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
            ))}
          </div>
          <p className="mt-4 text-xs text-fg-quaternary">
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
