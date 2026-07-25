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
        "hairline-top relative flex flex-col rounded-2xl p-6",
        featured
          ? "bg-surface-raised ring-2 ring-accent shadow-xl"
          : "bg-surface-raised/60 ring-1 ring-border-subtle",
      )}
    >
      {featured && (
        <span className="absolute -top-3 left-6 rounded-full bg-accent px-2.5 py-0.5 text-2xs font-semibold uppercase tracking-widest text-accent-contrast">
          Most picked
        </span>
      )}

      <h3 className="text-sm font-medium text-fg">{name}</h3>

      <div className="mt-4 flex items-baseline gap-1.5">
        <span className="font-mono text-3xl font-semibold tabular-nums text-fg">
          {pricePaise === 0 ? "Free" : formatPaise(pricePaise)}
        </span>
        {cadence && (
          <span className="text-xs text-fg-quaternary">
            {cadence === "one-time" ? "once" : `/ ${cadence}`}
          </span>
        )}
      </div>

      {note && <p className="mt-1.5 text-2xs text-fg-quaternary">{note}</p>}

      <ul className="mt-6 flex-1 space-y-2.5">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2.5 text-sm text-fg-secondary">
            <Check
              className={cn("mt-0.5 size-3.5 shrink-0", featured ? "text-accent" : "text-success")}
            />
            <span className="leading-snug">{f}</span>
          </li>
        ))}
      </ul>

      <ButtonLink
        href={href}
        variant={featured ? "primary" : "secondary"}
        className="mt-7 w-full"
      >
        {cta}
      </ButtonLink>
    </div>
  );
}
