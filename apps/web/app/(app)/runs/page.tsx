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
  if (score >= 80) return "border-success/30 bg-success-subtle text-success";
  if (score >= 60) return "border-accent/40 bg-accent-subtle text-accent-text";
  return "border-warning/30 bg-warning-subtle text-warning";
}

export default function RunsPage() {
  return (
    <div className="space-y-8">
      <Reveal className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow flex items-center gap-2">
            <span className="inline-block h-px w-6 bg-accent" />
            History
          </p>
          <h1 className="type-display mt-3 text-3xl text-fg sm:text-4xl">Runs</h1>
          <p className="mt-2 font-mono text-2xs uppercase tracking-wide text-fg-quaternary">
            Every resume you have tailored, with its score
          </p>
        </div>
        <ButtonLink href="/tailor" variant="secondary">
          <Sparkles className="size-4" />
          New run
        </ButtonLink>
      </Reveal>

      <Reveal delay={80}>
        {/* Framed table-like list with a mono column header */}
        <div className="overflow-hidden rounded-md border border-border-strong bg-surface-raised">
          <div className="hidden items-center gap-x-4 border-b border-border-subtle bg-surface-sunken px-5 py-2.5 sm:flex">
            <span className="w-2.5" />
            <span className="mono-label flex-1">Company / Role</span>
            <span className="mono-label w-24">Date</span>
            <span className="mono-label w-14 text-right">Score</span>
            <span className="w-8" />
          </div>

          <ul className="divide-y divide-border-subtle">
            {runs.map((run) => (
              <li
                key={run.id}
                className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-4 transition-colors duration-fast hover:bg-surface-sunken"
              >
                <Status status={run.status} />

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-fg">{run.company}</p>
                  <p className="truncate text-xs text-fg-quaternary">{run.role}</p>
                </div>

                <span className="w-24 shrink-0 font-mono text-2xs text-fg-quaternary">{run.date}</span>

                <span className="flex w-14 shrink-0 justify-end">
                  {run.score !== null ? (
                    <span
                      className={cn(
                        "rounded-[2px] border px-2 py-0.5 font-mono text-2xs font-medium tabular-nums",
                        scoreTone(run.score),
                      )}
                    >
                      {run.score}
                    </span>
                  ) : (
                    <span className="rounded-[2px] border border-border-subtle px-2 py-0.5 font-mono text-2xs uppercase text-fg-tertiary">
                      {run.status === "running" ? "···" : "—"}
                    </span>
                  )}
                </span>

                <button
                  type="button"
                  disabled={run.status !== "succeeded"}
                  aria-label={`Download resume for ${run.company}`}
                  className="grid size-8 shrink-0 place-items-center rounded-md border border-border-default text-fg-tertiary transition-colors hover:border-border-strong hover:text-fg disabled:pointer-events-none disabled:opacity-30"
                >
                  <Download className="size-4" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      </Reveal>
    </div>
  );
}

function Status({ status }: { status: string }) {
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
