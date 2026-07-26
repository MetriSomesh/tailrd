import { ButtonLink } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { formatPaise } from "@/lib/site";
import { Check } from "lucide-react";

export interface PlanCardProps {
  name: string;
  pricePaise: number;
  cadence: string | null;
  features: readonly string[];
  cta: string;
  href: string;
  featured?: boolean;
  note?: string;
}

export function PlanCard({
  name,
  pricePaise,
  cadence,
  features,
  cta,
  href,
  featured = false,
  note,
}: PlanCardProps) {
  return (
    <div
      className={cn(
        "relative flex w-full flex-col rounded-md border bg-surface-raised",
        featured ? "border-border-strong hard-shadow" : "border-border-default",
      )}
    >
      {/* Header band */}
      <div
        className={cn(
          "flex items-center justify-between border-b px-5 py-3",
          featured ? "border-border-strong bg-accent" : "border-border-subtle",
        )}
      >
        <span
          className={cn(
            "font-mono text-2xs uppercase tracking-widest",
            featured ? "text-accent-contrast" : "text-fg-tertiary",
          )}
        >
          {name}
        </span>
        {featured && (
          <span className="font-mono text-2xs font-semibold uppercase tracking-wide text-accent-contrast">
            ★ Most picked
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-baseline gap-1.5">
          <span className="type-display text-4xl tabular-nums text-fg">
            {pricePaise === 0 ? "Free" : formatPaise(pricePaise)}
          </span>
          {cadence && (
            <span className="font-mono text-2xs text-fg-quaternary">
              {cadence === "one-time" ? "once" : `/ ${cadence}`}
            </span>
          )}
        </div>

        {note && <p className="mt-2 font-mono text-2xs text-fg-quaternary">{note}</p>}

        <ul className="mt-6 flex-1 space-y-0 divide-y divide-border-subtle border-y border-border-subtle">
          {features.map((f) => (
            <li key={f} className="flex items-start gap-2.5 py-2.5 text-sm text-fg-secondary">
              <Check
                className={cn(
                  "mt-0.5 size-3.5 shrink-0",
                  featured ? "text-accent-text" : "text-fg-tertiary",
                )}
              />
              <span className="leading-snug">{f}</span>
            </li>
          ))}
        </ul>

        <ButtonLink
          href={href}
          variant={featured ? "primary" : "secondary"}
          className="mt-6 w-full"
        >
          {cta}
        </ButtonLink>
      </div>
    </div>
  );
}
