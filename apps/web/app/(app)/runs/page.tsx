import { Reveal } from "@/components/motion/reveal";
import { ButtonLink } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { Download, Sparkles } from "lucide-react";

const runs = [
  { id: "r1", company: "Lexi", role: "AI Engineer", score: 84.5, status: "succeeded", date: "25 Jul 2026" },
  { id: "r2", company: "Stripe", role: "Backend Engineer", score: null, status: "running", date: "25 Jul 2026" },
  { id: "r3", company: "Vercel", role: "Full Stack Engineer", score: 71.2, status: "succeeded", date: "24 Jul 2026" },
  { id: "r4", company: "Razorpay", role: "SDE-2", score: null, status: "failed", date: "23 Jul 2026" },
];

function scoreTone(score: number) {
  if (score >= 80) return "bg-success-subtle text-success";
  if (score >= 60) return "bg-accent-subtle text-accent";
  return "bg-warning-subtle text-warning";
}

export default function RunsPage() {
  return (
    <div className="space-y-8">
      <Reveal className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="type-display text-3xl text-fg sm:text-4xl">Runs</h1>
          <p className="mt-1.5 text-sm text-fg-tertiary">
            Every resume you have tailored, with its score.
          </p>
        </div>
        <ButtonLink href="/tailor" variant="secondary">
          <Sparkles className="size-4" />
          New run
        </ButtonLink>
      </Reveal>

      <Reveal delay={80}>
        {/* Single bordered table-like list. Reads cleanly and stays aligned. */}
        <ul className="divide-y divide-border-subtle overflow-hidden rounded-2xl bg-surface-raised ring-1 ring-border-subtle">
          {runs.map((run) => (
            <li
              key={run.id}
              className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-4 transition-colors duration-fast hover:bg-surface-overlay/50"
            >
              <Status status={run.status} />

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-fg">{run.company}</p>
                <p className="truncate text-xs text-fg-quaternary">{run.role}</p>
              </div>

              <span className="shrink-0 font-mono text-2xs text-fg-quaternary">{run.date}</span>

              {run.score !== null ? (
                <span
                  className={cn(
                    "shrink-0 rounded-full px-2.5 py-1 font-mono text-2xs font-medium tabular-nums",
                    scoreTone(run.score),
                  )}
                >
                  {run.score}%
                </span>
              ) : (
                <span className="shrink-0 rounded-full bg-surface-overlay px-2.5 py-1 text-2xs font-medium text-fg-tertiary">
                  {run.status}
                </span>
              )}

              <button
                type="button"
                disabled={run.status !== "succeeded"}
                aria-label={`Download resume for ${run.company}`}
                className="grid size-8 shrink-0 place-items-center rounded-lg text-fg-tertiary transition-colors hover:bg-surface-overlay hover:text-fg disabled:pointer-events-none disabled:opacity-30"
              >
                <Download className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      </Reveal>
    </div>
  );
}

function Status({ status }: { status: string }) {
  // role="img" is required for aria-label to be valid on a generic element.
  const running = status === "running" || status === "queued";
  if (running) {
    return (
      <span role="img" aria-label={status} className="relative flex size-2.5 shrink-0">
        <span
          aria-hidden="true"
          className="absolute inline-flex size-full animate-ping rounded-full bg-accent opacity-60"
        />
        <span aria-hidden="true" className="relative inline-flex size-2.5 rounded-full bg-accent" />
      </span>
    );
  }
  return (
    <span
      role="img"
      aria-label={status}
      className={cn(
        "size-2.5 shrink-0 rounded-full",
        status === "succeeded" ? "bg-success" : "bg-danger",
      )}
    />
  );
}
