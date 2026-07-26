"use client";

import { Reveal } from "@/components/motion/reveal";
import { Button, ButtonLink } from "@/components/ui/button";
import {
  ApiRequestError,
  cancelSubscription,
  confirmPayment,
  createCreditOrder,
  createSubscription,
  getUsage,
} from "@/lib/api";
import { cn } from "@/lib/cn";
import { PRICING, formatPaise } from "@/lib/site";
import { useAsync } from "@/lib/use-async";
import { Check } from "lucide-react";
import { useState } from "react";

const options = [
  {
    id: "per" as const,
    name: PRICING.perResume.name,
    pricePaise: PRICING.perResume.pricePaise,
    cadence: "once",
    features: ["1 resume credit", "Never expires"],
    cta: "Buy credit",
  },
  {
    id: "weekly" as const,
    name: PRICING.weekly.name,
    pricePaise: PRICING.weekly.pricePaise,
    cadence: "week",
    features: ["Unlimited 7 days", "15 a day fair use"],
    cta: "Subscribe",
    featured: true,
  },
  {
    id: "monthly" as const,
    name: PRICING.monthly.name,
    pricePaise: PRICING.monthly.pricePaise,
    cadence: "month",
    features: ["Unlimited 30 days", "Best value"],
    cta: "Subscribe",
  },
];

export default function BillingPage() {
  const { data: usage, loading, refetch } = useAsync(() => getUsage(), []);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  async function run(key: string, fn: () => Promise<unknown>, okText: string) {
    setBusy(key);
    setNotice(null);
    try {
      await fn();
      setNotice({ kind: "ok", text: okText });
      refetch();
    } catch (err) {
      setNotice({
        kind: "err",
        text: err instanceof ApiRequestError ? err.problem.detail : "Something went wrong.",
      });
    } finally {
      setBusy(null);
    }
  }

  async function buyCredit() {
    const order = await createCreditOrder();
    // Mock provider: verification always succeeds, so we can confirm inline.
    // With real Razorpay this is where the checkout modal would open instead.
    if (order.key_id === "mock_key") {
      await confirmPayment({
        order_id: order.order_id,
        payment_id: `pay_mock_${Date.now()}`,
        signature: "mock_signature",
      });
    } else {
      throw new ApiRequestError({
        code: "checkout_unavailable",
        title: "Checkout unavailable",
        detail: "Live card checkout isn't enabled in this environment yet.",
        status: 400,
      });
    }
  }

  const pct = usage ? Math.round((usage.free_used / Math.max(usage.free_limit, 1)) * 100) : 0;

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

      {notice && (
        <Reveal>
          <div
            role="status"
            className={cn(
              "rounded-md border px-4 py-3 text-sm",
              notice.kind === "ok"
                ? "border-success/40 bg-success-subtle text-success"
                : "border-danger/40 bg-danger-subtle text-danger",
            )}
          >
            {notice.text}
          </div>
        </Reveal>
      )}

      {/* Current usage */}
      <Reveal delay={70}>
        <section className="rounded-md border border-border-default bg-surface-raised">
          <div className="grid grid-cols-2 divide-x divide-border-subtle border-b border-border-subtle">
            <div className="p-5">
              <p className="mono-label">Current plan</p>
              <p className="type-display mt-2 text-2xl text-fg">
                {loading ? "…" : usage?.has_subscription ? "Unlimited" : "Free"}
              </p>
              {usage?.has_subscription && usage.subscription_ends && (
                <p className="mt-1 font-mono text-2xs text-fg-quaternary">
                  {usage.subscription_plan} · renews {new Date(usage.subscription_ends).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
                </p>
              )}
            </div>
            <div className="p-5">
              <p className="mono-label">Credits</p>
              <p className="type-display mt-2 text-2xl tabular-nums text-fg">
                {loading ? "…" : (usage?.credit_balance ?? 0)}
              </p>
            </div>
          </div>

          <div className="space-y-2 p-5">
            <div className="flex items-baseline justify-between gap-2">
              <span className="mono-label">Free resumes this month</span>
              <span className="font-mono text-2xs tabular-nums text-fg-secondary">
                {usage ? `${usage.free_used} / ${usage.free_limit}` : "—"}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-[1px] bg-surface-sunken"
              role="progressbar"
              aria-valuenow={usage?.free_used ?? 0}
              aria-valuemin={0}
              aria-valuemax={usage?.free_limit ?? 3}
              aria-label="Free resume usage"
            >
              <div className="h-full bg-accent transition-[width] duration-slow" style={{ width: `${pct}%` }} />
            </div>
            <p className="font-mono text-2xs text-fg-quaternary">
              {usage ? `${usage.free_remaining} remaining · resets on the 1st` : "\u00a0"}
            </p>
          </div>

          {usage?.has_subscription && (
            <div className="border-t border-border-subtle p-5">
              <Button
                variant="secondary"
                size="sm"
                loading={busy === "cancel"}
                onClick={() =>
                  run("cancel", cancelSubscription, "Subscription will cancel at period end.")
                }
              >
                Cancel subscription
              </Button>
            </div>
          )}
        </section>
      </Reveal>

      {/* Upgrade options */}
      <Reveal delay={140}>
        <section>
          <h2 className="mono-label">Add capacity</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {options.map((o) => {
              const isSub = o.id === "weekly" || o.id === "monthly";
              const disabled = usage?.has_subscription && isSub;
              return (
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
                      disabled={disabled}
                      loading={busy === o.id}
                      onClick={() =>
                        o.id === "per"
                          ? run("per", buyCredit, "Credit added to your balance.")
                          : run(
                              o.id,
                              () => createSubscription(o.id),
                              `${o.name} subscription active.`,
                            )
                      }
                    >
                      {disabled ? "Current plan" : o.cta}
                    </Button>
                  </div>
                </div>
              );
            })}
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
