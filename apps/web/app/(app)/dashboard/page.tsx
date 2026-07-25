import { Reveal } from "@/components/motion/reveal";
import { ButtonLink } from "@/components/ui/button";
import { ScoreGauge } from "@/components/ui/score-gauge";
import { cn } from "@/lib/cn";
import { ArrowUpRight, Check, FileText, Sparkles, TrendingUp, Wallet, X } from "lucide-react";

// Mock data — replaced by API calls when auth is wired to the frontend.
const usage = { freeUsed: 1, freeLimit: 3, credits: 0, hasSubscription: false };
const latest = {
  score: 84.5,
  company: "Lexi",
  role: "AI Engineer",
  subScores: [
    { label: "Keywords", value: 56 },
    { label: "Skills", value: 100 },
    { label: "Terms", value: 100 },
    { label: "Experience", value: 100 },
  ],
  covered: ["LLM agents", "Retrieval", "Backend APIs", "Evals"],
  missing: ["Kubernetes"],
};
const recent = [
  { id: "1", company: "Lexi", role: "AI Engineer", score: 84.5, status: "succeeded", date: "25 Jul" },
  { id: "2", company: "Stripe", role: "Backend Engineer", score: null, status: "running", date: "25 Jul" },
  { id: "3", company: "Vercel", role: "Full Stack", score: 71.2, status: "succeeded", date: "24 Jul" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Page header */}
      <Reveal className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="type-display text-3xl text-fg sm:text-4xl">Dashboard</h1>
          <p className="mt-1.5 text-sm text-fg-tertiary">
            {usage.freeLimit - usage.freeUsed} of {usage.freeLimit} free resumes left this month.
          </p>
        </div>
        <ButtonLink href="/tailor">
          <Sparkles className="size-4" />
          Tailor a resume
        </ButtonLink>
      </Reveal>

      {/* Stat strip — single bordered row, not three floating cards */}
      <Reveal delay={60}>
        <div className="grid gap-px overflow-hidden rounded-2xl bg-border-subtle ring-1 ring-border-subtle sm:grid-cols-3">
          <Stat
            Icon={FileText}
            label="Free usage"
            value={`${usage.freeUsed}/${usage.freeLimit}`}
            hint="resets on the 1st"
          />
          <Stat Icon={Wallet} label="Credits" value={String(usage.credits)} hint="never expire" />
          <Stat
            Icon={TrendingUp}
            label="Best score"
            value={`${latest.score}%`}
            hint={`${latest.company} — ${latest.role}`}
          />
        </div>
      </Reveal>

      {/* Latest result + recent runs */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        {/* Latest result panel */}
        <Reveal delay={120}>
          <section className="hairline-top flex h-full flex-col rounded-2xl bg-surface-raised p-6 ring-1 ring-border-subtle">
            <header className="flex items-baseline justify-between gap-3">
              <h2 className="text-sm font-medium text-fg">Latest result</h2>
              <span className="font-mono text-2xs text-fg-quaternary">{latest.company}</span>
            </header>

            <div className="mt-6 flex justify-center">
              <ScoreGauge score={latest.score} size="lg" />
            </div>

            <div className="mt-7 space-y-3">
              {latest.subScores.map((s) => (
                <div key={s.label} className="space-y-1.5">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-2xs text-fg-tertiary">{s.label}</span>
                    <span className="font-mono text-2xs tabular-nums text-fg-secondary">
                      {s.value}%
                    </span>
                  </div>
                  <div className="h-1 overflow-hidden rounded-full bg-border-subtle">
                    <div className="h-full rounded-full bg-accent" style={{ width: `${s.value}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </Reveal>

        {/* Right column: gaps + recent runs */}
        <div className="space-y-6">
          {/* Gap panel */}
          <Reveal delay={180}>
            <section className="hairline-top rounded-2xl bg-surface-raised p-6 ring-1 ring-border-subtle">
              <h2 className="text-sm font-medium text-fg">Requirement coverage</h2>
              <p className="mt-1 text-xs text-fg-quaternary">
                What the posting asked for, and what your resume answers.
              </p>
              <div className="mt-4 flex flex-wrap gap-1.5">
                {latest.covered.map((c) => (
                  <span
                    key={c}
                    className="inline-flex items-center gap-1.5 rounded-full bg-success-subtle px-2.5 py-1 text-2xs font-medium text-success"
                  >
                    <Check className="size-3" />
                    {c}
                  </span>
                ))}
                {latest.missing.map((m) => (
                  <span
                    key={m}
                    className="inline-flex items-center gap-1.5 rounded-full bg-danger-subtle px-2.5 py-1 text-2xs font-medium text-danger"
                  >
                    <X className="size-3" />
                    {m}
                  </span>
                ))}
              </div>
            </section>
          </Reveal>

          {/* Recent runs */}
          <Reveal delay={240}>
            <section className="hairline-top rounded-2xl bg-surface-raised p-6 ring-1 ring-border-subtle">
              <header className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-medium text-fg">Recent runs</h2>
                <ButtonLink href="/runs" variant="ghost" size="sm">
                  View all
                  <ArrowUpRight className="size-3.5" />
                </ButtonLink>
              </header>

              <ul className="mt-4 divide-y divide-border-subtle">
                {recent.map((r) => (
                  <li key={r.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                    <StatusDot status={r.status} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-fg">
                        {r.company}
                        <span className="text-fg-quaternary"> · {r.role}</span>
                      </p>
                    </div>
                    <span className="shrink-0 font-mono text-2xs text-fg-quaternary">{r.date}</span>
                    {r.score !== null ? (
                      <span className="shrink-0 rounded-full bg-surface-overlay px-2 py-0.5 font-mono text-2xs tabular-nums text-fg-secondary">
                        {r.score}%
                      </span>
                    ) : (
                      <span className="shrink-0 rounded-full bg-accent-subtle px-2 py-0.5 text-2xs font-medium text-accent">
                        {r.status}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          </Reveal>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function Stat({
  Icon,
  label,
  value,
  hint,
}: {
  Icon: typeof FileText;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="bg-surface-base p-5 transition-colors duration-normal hover:bg-surface-raised">
      <div className="flex items-center gap-2">
        <Icon className="size-3.5 text-fg-quaternary" aria-hidden="true" />
        <span className="text-2xs font-medium uppercase tracking-widest text-fg-tertiary">
          {label}
        </span>
      </div>
      <div className="mt-2.5">
        <span className="font-mono text-2xl font-semibold tabular-nums text-fg">{value}</span>
        <span className="mt-0.5 block text-xs text-fg-quaternary">{hint}</span>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  // role="img" is required for aria-label to be valid on a generic element.
  if (status === "running" || status === "queued") {
    return (
      <span role="img" aria-label={status} className="relative flex size-2 shrink-0">
        <span
          aria-hidden="true"
          className="absolute inline-flex size-full animate-ping rounded-full bg-accent opacity-60"
        />
        <span aria-hidden="true" className="relative inline-flex size-2 rounded-full bg-accent" />
      </span>
    );
  }
  return (
    <span
      role="img"
      aria-label={status}
      className={cn(
        "size-2 shrink-0 rounded-full",
        status === "succeeded" ? "bg-success" : "bg-danger",
      )}
    />
  );
}
