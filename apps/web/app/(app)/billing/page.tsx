import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PRICING, formatPaise } from "@/lib/site";
import { Check } from "lucide-react";

/**
 * Billing page — shows current plan, usage, and upgrade options.
 */
export default function BillingPage() {
  // Mock current state
  const _currentPlan = "free";
  const usage = { free_used: 1, free_limit: 3, credit_balance: 0 };

  const plans = [
    { ...PRICING.perResume, features: ["1 resume credit", "Never expires", "₹29 per use"] },
    { ...PRICING.weekly, features: ["Unlimited for 7 days", "15/day fair use", "Cancel anytime"] },
    { ...PRICING.monthly, features: ["Unlimited for 30 days", "15/day fair use", "Best value"] },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-medium text-fg">Billing</h1>
        <p className="mt-1 text-sm text-fg-tertiary">Manage your plan and credits.</p>
      </div>

      {/* Current usage */}
      <Card>
        <CardHeader>
          <CardTitle>Current usage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-6">
            <div>
              <p className="text-3xl font-semibold tabular-nums text-fg">{usage.free_used}/{usage.free_limit}</p>
              <p className="text-xs text-fg-quaternary">free resumes used this month</p>
            </div>
            <div className="h-10 w-px bg-border-subtle" />
            <div>
              <p className="text-3xl font-semibold tabular-nums text-fg">{usage.credit_balance}</p>
              <p className="text-xs text-fg-quaternary">credits available</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Plans */}
      <div>
        <h2 className="mb-4 text-lg font-medium text-fg">Upgrade</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {plans.map((plan) => (
            <Card key={plan.id} className="flex flex-col justify-between">
              <div>
                <CardHeader>
                  <CardTitle>{plan.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-semibold text-fg">{formatPaise(plan.pricePaise)}</p>
                  <p className="mt-0.5 text-xs text-fg-quaternary">
                    {plan.cadence === "one-time" ? "one-time" : `per ${plan.cadence}`}
                  </p>
                  <ul className="mt-4 space-y-2">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-center gap-2 text-xs text-fg-secondary">
                        <Check className="h-3.5 w-3.5 text-success flex-shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </div>
              <div className="mt-5 px-5 pb-5">
                <Button variant="secondary" size="sm" className="w-full">
                  {plan.cadence === "one-time" ? "Buy credit" : "Subscribe"}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
