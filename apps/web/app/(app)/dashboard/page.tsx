"use client";

import { useUser } from "@/components/app/require-auth";
import { Reveal } from "@/components/motion/reveal";
import { ButtonLink } from "@/components/ui/button";
import { ScoreGauge } from "@/components/ui/score-gauge";
import { type RunDetail, type RunSummary, getRun, getUsage, listRuns } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useAsync } from "@/lib/use-async";
import { ArrowUpRight, Check, FileText, MailWarning, Sparkles, TrendingUp, Wallet, X } from "lucide-react";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

export default function DashboardPage() {
  const user = useUser();

  // Runs and usage are fetched independently: a brand-new (unverified) user can
  // read their runs but not usage (that needs a verified email), so one failing
  // must not blank the whole page.
  const { data: runs, loading, error } = useAsync(() => listRuns(), []);
  const { data: usage, loading: usageLoading } = useAsync(() => getUsage(), []);

  // The most recent run that actually produced a score.
  const latest = runs?.find((r) => r.status === "succeeded" && r.overall_score != null) ?? null;

  // Fetch the latest run's detail once and share it across panels.
  const { data: latestDetail } = useAsync<RunDetail | null>(
    () => (latest ? getRun(latest.id) : Promise.resolve(null)),
    [latest?.id],
  );
  const bestScore = runs?.reduce<number | null>(
    (best, r) => (r.overall_score != null && (best == null || r.overall_score > best) ? r.overall_score : best),
    null,
  );

  return (
    <div className="space-y-8">
      <Reveal className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow flex items-center gap-2">
            <span className="inline-block h-px w-6 bg-accent" />
            Overview
          </p>
          <h1 className="type-display mt-3 text-3xl text-fg sm:text-4xl">Dashboard</h1>
          <p className="mt-2 font-mono text-2xs uppercase tracking-wide text-fg-quaternary">
            {usage
              ? usage.has_subscription
                ? "Unlimited plan active"
                : `${usage.free_remaining} of ${usage.free_limit} free resumes left this month`
              : "\u00a0"}
          </p>
        </div>
        <ButtonLink href="/tailor">
          <Sparkles className="size-4" />
          Tailor a resume
        </ButtonLink>
      </Reveal>

      {!user.email_verified && (
        <Reveal delay={30}>
          <div className="flex items-start gap-3 rounded-md border border-warning/40 bg-warning-subtle px-4 py-3">
            <MailWarning className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
            <p className="text-sm text-fg-secondary">
              <span className="font-medium text-fg">Verify your email</span> to start tailoring
              resumes. We sent a link to {user.email}.
            </p>
          </div>
        </Reveal>
      )}

      {error ? (
        <ErrorPanel />
      ) : (
        <>
          {/* Stat strip */}
          <Reveal delay={60}>
            <div className="grid overflow-hidden rounded-md border border-border-strong sm:grid-cols-3">
              <Stat
                Icon={FileText}
                label="Free usage"
                value={usage ? `${usage.free_used}/${usage.free_limit}` : usageLoading ? null : "\u2014"}
                hint="resets on the 1st"
                className="border-b border-border-subtle sm:border-b-0 sm:border-r"
              />
              <Stat
                Icon={Wallet}
                label="Credits"
                value={usage ? String(usage.credit_balance) : usageLoading ? null : "\u2014"}
                hint="never expire"
                className="border-b border-border-subtle sm:border-b-0 sm:border-r"
              />
              <Stat
                Icon={TrendingUp}
                label="Best score"
                value={loading ? null : bestScore != null ? `${bestScore}%` : "n/a"}
                hint={latest ? `${latest.company ?? "Latest"} · ${latest.role ?? "role"}` : "no runs yet"}
              />
            </div>
          </Reveal>

          {loading ? (
            <LoadingPanels />
          ) : !runs || runs.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
              <LatestResult latest={latest} detail={latestDetail ?? null} />
              <div className="space-y-6">
                <Coverage latest={latest} detail={latestDetail ?? null} />
                <RecentRuns runs={runs.slice(0, 5)} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

function LatestResult({ latest, detail }: { latest: RunSummary | null; detail: RunDetail | null }) {
  if (!latest) {
    return (
      <Reveal delay={120}>
        <section className="flex h-full flex-col items-center justify-center rounded-md border border-border-default bg-surface-raised p-8 text-center">
          <h2 className="mono-label">Latest result</h2>
          <p className="mt-3 text-sm text-fg-tertiary">
            No scored resume yet. Your latest score will show here.
          </p>
        </section>
      </Reveal>
    );
  }

  const score = detail?.score_json;
  const subScores = score
    ? [
        { label: "Keywords", value: Math.round(score.keyword_match_pct) },
        { label: "Skills", value: Math.round(score.skills_match_pct) },
        { label: "Terms", value: Math.round(score.term_overlap_pct) },
        { label: "Experience", value: Math.round(score.experience_relevance_pct) },
      ]
    : [];

  return (
    <Reveal delay={120}>
      <section className="flex h-full flex-col rounded-md border border-border-default bg-surface-raised">
        <header className="flex items-center justify-between gap-3 border-b border-border-subtle px-5 py-3">
          <h2 className="mono-label">Latest result</h2>
          <span className="font-mono text-2xs text-fg-tertiary">{latest.company ?? "—"}</span>
        </header>

        <div className="flex flex-col p-5">
          <div className="flex justify-center">
            <ScoreGauge score={latest.overall_score ?? 0} size="lg" />
          </div>

          {subScores.length > 0 && (
            <div className="mt-6 divide-y divide-border-subtle border-y border-border-subtle">
              {subScores.map((s) => (
                <div key={s.label} className="flex items-center gap-3 py-2.5">
                  <span className="mono-label w-24 shrink-0">{s.label}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-[1px] bg-surface-sunken">
                    <div className="h-full bg-accent" style={{ width: `${s.value}%` }} />
                  </div>
                  <span className="w-10 shrink-0 text-right font-mono text-2xs tabular-nums text-fg-secondary">
                    {s.value}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </Reveal>
  );
}

function Coverage({ latest, detail }: { latest: RunSummary | null; detail: RunDetail | null }) {
  const score = detail?.score_json;
  const covered = score?.skills_matched.slice(0, 8) ?? [];
  const missing = score?.skills_missing.slice(0, 6) ?? [];

  return (
    <Reveal delay={180}>
      <section className="rounded-md border border-border-default bg-surface-raised p-5">
        <h2 className="mono-label">Requirement coverage</h2>
        <p className="mt-1.5 text-xs text-fg-quaternary">
          What the posting asked for, and what your resume answers.
        </p>
        {covered.length === 0 && missing.length === 0 ? (
          <p className="mt-4 text-sm text-fg-tertiary">
            {latest ? "No skill breakdown for this run." : "Tailor a resume to see coverage."}
          </p>
        ) : (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {covered.map((c) => (
              <span
                key={c}
                className="inline-flex items-center gap-1.5 rounded-[2px] border border-success/30 bg-success-subtle px-2.5 py-1 font-mono text-2xs text-success"
              >
                <Check className="size-3" />
                {c}
              </span>
            ))}
            {missing.map((m) => (
              <span
                key={m}
                className="inline-flex items-center gap-1.5 rounded-[2px] border border-danger/30 bg-danger-subtle px-2.5 py-1 font-mono text-2xs text-danger"
              >
                <X className="size-3" />
                {m}
              </span>
            ))}
          </div>
        )}
      </section>
    </Reveal>
  );
}

function RecentRuns({ runs }: { runs: RunSummary[] }) {
  return (
    <Reveal delay={240}>
      <section className="rounded-md border border-border-default bg-surface-raised">
        <header className="flex items-center justify-between gap-3 border-b border-border-subtle px-5 py-3">
          <h2 className="mono-label">Recent runs</h2>
          <ButtonLink href="/runs" variant="ghost" size="sm" className="h-auto px-1 py-0">
            View all
            <ArrowUpRight className="size-3.5" />
          </ButtonLink>
        </header>

        <ul className="divide-y divide-border-subtle">
          {runs.map((r) => (
            <li key={r.id} className="flex items-center gap-3 px-5 py-3">
              <StatusDot status={r.status} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-fg">
                  {r.company ?? r.jd_label ?? "Untitled run"}
                  {r.role && <span className="text-fg-quaternary"> · {r.role}</span>}
                </p>
              </div>
              <span className="shrink-0 font-mono text-2xs text-fg-quaternary">
                {fmtDate(r.created_at)}
              </span>
              {r.overall_score != null ? (
                <span className="shrink-0 rounded-[2px] border border-border-subtle px-2 py-0.5 font-mono text-2xs tabular-nums text-fg-secondary">
                  {r.overall_score}%
                </span>
              ) : (
                <span className="shrink-0 rounded-[2px] border border-accent/40 bg-accent-subtle px-2 py-0.5 font-mono text-2xs uppercase text-accent-text">
                  {r.status}
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>
    </Reveal>
  );
}

function EmptyState() {
  return (
    <Reveal delay={120}>
      <section className="flex flex-col items-center rounded-md border border-border-default bg-surface-raised px-6 py-16 text-center">
        <div className="grid size-12 place-items-center rounded-md border border-border-default text-fg">
          <Sparkles className="size-5" />
        </div>
        <h2 className="type-display mt-5 text-2xl text-fg">No runs yet</h2>
        <p className="mt-2 max-w-sm text-sm text-fg-tertiary">
          Paste a job description and we&apos;ll tailor your resume for it, then score the result
          against real ATS criteria.
        </p>
        <ButtonLink href="/tailor" className="mt-6">
          <Sparkles className="size-4" />
          Tailor your first resume
        </ButtonLink>
      </section>
    </Reveal>
  );
}

function LoadingPanels() {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
      <div className="skeleton h-80 rounded-md" />
      <div className="space-y-6">
        <div className="skeleton h-28 rounded-md" />
        <div className="skeleton h-56 rounded-md" />
      </div>
    </div>
  );
}

function ErrorPanel() {
  return (
    <div className="rounded-md border border-danger/40 bg-danger-subtle px-5 py-4 text-sm text-danger">
      Couldn&apos;t load your dashboard data. Refresh the page to try again.
    </div>
  );
}

function Stat({
  Icon,
  label,
  value,
  hint,
  className,
}: {
  Icon: typeof FileText;
  label: string;
  value: string | null;
  hint: string;
  className?: string;
}) {
  return (
    <div className={cn("bg-surface-raised p-5", className)}>
      <div className="flex items-center gap-2">
        <Icon className="size-3.5 text-fg-quaternary" aria-hidden="true" />
        <span className="mono-label">{label}</span>
      </div>
      <div className="mt-3">
        {value == null ? (
          <span className="skeleton block h-8 w-16 rounded" />
        ) : (
          <span className="type-display text-3xl text-fg">{value}</span>
        )}
        <span className="mt-1 block font-mono text-2xs text-fg-quaternary">{hint}</span>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
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
