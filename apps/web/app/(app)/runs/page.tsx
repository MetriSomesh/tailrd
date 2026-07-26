"use client";

import { Reveal } from "@/components/motion/reveal";
import { ButtonLink } from "@/components/ui/button";
import { type RunSummary, downloadRunUrl, listRuns } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useAsync } from "@/lib/use-async";
import { Download, Sparkles } from "lucide-react";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function scoreTone(score: number): string {
  if (score >= 80) return "border-success/30 bg-success-subtle text-success";
  if (score >= 60) return "border-accent/40 bg-accent-subtle text-accent-text";
  return "border-warning/30 bg-warning-subtle text-warning";
}

export default function RunsPage() {
  const { data: runs, loading, error } = useAsync(() => listRuns(), []);

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
        {error ? (
          <div className="rounded-md border border-danger/40 bg-danger-subtle px-5 py-4 text-sm text-danger">
            Couldn&apos;t load your runs. Refresh to try again.
          </div>
        ) : loading ? (
          <div className="skeleton h-64 rounded-md" />
        ) : !runs || runs.length === 0 ? (
          <div className="flex flex-col items-center rounded-md border border-border-default bg-surface-raised px-6 py-16 text-center">
            <div className="grid size-12 place-items-center rounded-md border border-border-default text-fg">
              <Sparkles className="size-5" />
            </div>
            <h2 className="type-display mt-5 text-2xl text-fg">No runs yet</h2>
            <p className="mt-2 max-w-sm text-sm text-fg-tertiary">
              Once you tailor a resume, each run shows up here with its ATS score and a download.
            </p>
            <ButtonLink href="/tailor" className="mt-6">
              <Sparkles className="size-4" />
              Tailor your first resume
            </ButtonLink>
          </div>
        ) : (
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
                    <p className="truncate text-sm font-medium text-fg">
                      {run.company ?? run.jd_label ?? "Untitled run"}
                    </p>
                    <p className="truncate text-xs text-fg-quaternary">{run.role ?? "—"}</p>
                  </div>

                  <span className="w-24 shrink-0 font-mono text-2xs text-fg-quaternary">
                    {fmtDate(run.created_at)}
                  </span>

                  <span className="flex w-14 shrink-0 justify-end">
                    {run.overall_score != null ? (
                      <span
                        className={cn(
                          "rounded-[2px] border px-2 py-0.5 font-mono text-2xs font-medium tabular-nums",
                          scoreTone(run.overall_score),
                        )}
                      >
                        {run.overall_score}
                      </span>
                    ) : (
                      <span className="rounded-[2px] border border-border-subtle px-2 py-0.5 font-mono text-2xs uppercase text-fg-tertiary">
                        {run.status === "running" || run.status === "queued" ? "···" : "n/a"}
                      </span>
                    )}
                  </span>

                  {run.status === "succeeded" ? (
                    <a
                      href={downloadRunUrl(run.id)}
                      aria-label={`Download resume for ${run.company ?? "run"}`}
                      className="grid size-8 shrink-0 place-items-center rounded-md border border-border-default text-fg-tertiary transition-colors hover:border-border-strong hover:text-fg"
                    >
                      <Download className="size-4" />
                    </a>
                  ) : (
                    <span
                      aria-hidden="true"
                      className="grid size-8 shrink-0 place-items-center rounded-md border border-border-subtle text-fg-quaternary opacity-40"
                    >
                      <Download className="size-4" />
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Reveal>
    </div>
  );
}

function Status({ status }: { status: RunSummary["status"] }) {
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
