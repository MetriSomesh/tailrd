"use client";

import { Reveal } from "@/components/motion/reveal";
import { Button, ButtonLink } from "@/components/ui/button";
import {
  ApiRequestError,
  type RunDetail,
  type RunStage,
  downloadRunUrl,
  getRun,
  submitTailor,
} from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Download,
  Link2,
  Loader2,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

interface SubmitError {
  detail: string;
  code: string;
}

type Phase = "form" | "running" | "succeeded" | "failed";

const URL_RE = /^https?:\/\/\S+\.\S+/i;
const POLL_INTERVAL_MS = 1500;

/** Human-readable line shown under the bar, keyed off the backend stage. */
const STAGE_LABEL: Record<RunStage, string> = {
  queued: "Waiting in the queue…",
  scraping: "Reading the job posting…",
  building: "Assembling your base resume…",
  tailoring: "Rewriting your resume for this role…",
  generating: "Building your formatted document…",
  scoring: "Scoring against ATS criteria…",
  uploading: "Finishing up…",
  done: "Done",
  failed: "Something went wrong",
};

/** The visible checklist. Each step lights up once progress passes its mark. */
const STEPS: { label: string; at: number }[] = [
  { label: "Reading the posting", at: 5 },
  { label: "Tailoring your resume", at: 25 },
  { label: "Building the document", at: 80 },
  { label: "Scoring & finishing", at: 88 },
];

function scoreTone(score: number): string {
  if (score >= 80) return "border-success/30 bg-success-subtle text-success";
  if (score >= 60) return "border-accent/40 bg-accent-subtle text-accent-text";
  return "border-warning/30 bg-warning-subtle text-warning";
}

export default function TailorPage() {
  const [url, setUrl] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<Phase>("form");
  const [error, setError] = useState<SubmitError | null>(null);

  // Live run state while we wait.
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunDetail | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const validUrl = URL_RE.test(url.trim());
  const canSubmit = validUrl && !loading;

  const reset = useCallback(() => {
    if (pollRef.current) clearTimeout(pollRef.current);
    pollRef.current = null;
    setPhase("form");
    setRunId(null);
    setRun(null);
    setError(null);
    setUrl("");
    setCompany("");
    setRole("");
  }, []);

  // Poll the run until it reaches a terminal state.
  useEffect(() => {
    if (!runId || phase !== "running") return;

    let cancelled = false;
    let consecutiveErrors = 0;

    async function tick() {
      try {
        const detail = await getRun(runId as string);
        if (cancelled) return;
        consecutiveErrors = 0;
        setRun(detail);

        if (detail.status === "succeeded") {
          setPhase("succeeded");
          return;
        }
        if (detail.status === "failed" || detail.status === "cancelled") {
          setError({
            detail:
              detail.error_message ||
              "We couldn't finish this run. Your resume credit has been refunded if the failure was on our end.",
            code: detail.error_code || "run_failed",
          });
          setPhase("failed");
          return;
        }
      } catch {
        // Network blips shouldn't kill the wait — keep trying for a while.
        if (cancelled) return;
        consecutiveErrors += 1;
        if (consecutiveErrors >= 8) {
          setError({
            detail:
              "Lost connection while waiting for your run. It may still be processing — check the Runs page.",
            code: "poll_lost",
          });
          setPhase("failed");
          return;
        }
      }
      pollRef.current = setTimeout(tick, POLL_INTERVAL_MS);
    }

    pollRef.current = setTimeout(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [runId, phase]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      const res = await submitTailor({
        jd_url: url.trim(),
        company: company.trim() || undefined,
        role: role.trim() || undefined,
      });
      setRunId(res.run_id);
      setRun(null);
      setPhase("running");
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError({ detail: err.problem.detail, code: err.problem.code });
      } else {
        setError({ detail: "Something went wrong. Try again.", code: "unknown" });
      }
    } finally {
      setLoading(false);
    }
  }

  const needsOnboarding = error?.code.includes("onboarding");

  // -------------------------------------------------------------------------
  // Success
  // -------------------------------------------------------------------------
  if (phase === "succeeded" && run) {
    const score = run.overall_score;
    return (
      <Reveal className="mx-auto flex max-w-md flex-col items-center py-16 text-center">
        <div className="grid size-14 place-items-center rounded-md border border-success/40 bg-success-subtle">
          <CheckCircle2 className="size-6 text-success" />
        </div>
        <h1 className="type-display mt-6 text-3xl text-fg">Your resume is ready</h1>
        <p className="mt-3 text-pretty text-sm leading-relaxed text-fg-secondary">
          We rewrote your resume for this role and scored it against the posting.
        </p>

        {score != null && (
          <div className="mt-6 flex items-center gap-3">
            <span className="font-mono text-2xs uppercase tracking-wide text-fg-quaternary">
              ATS score
            </span>
            <span
              className={cn(
                "rounded-[3px] border px-3 py-1 font-mono text-lg font-medium tabular-nums",
                scoreTone(score),
              )}
            >
              {score}
            </span>
          </div>
        )}

        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <a href={downloadRunUrl(run.id)} download>
            <Button size="lg">
              <Download className="size-4" />
              Download DOCX
            </Button>
          </a>
          <ButtonLink href="/runs" variant="secondary">
            View in runs
            <ArrowRight className="size-4" />
          </ButtonLink>
        </div>
        <button
          type="button"
          onClick={reset}
          className="mt-6 font-mono text-2xs uppercase tracking-wide text-fg-tertiary underline-offset-4 hover:text-fg hover:underline"
        >
          Tailor another
        </button>
      </Reveal>
    );
  }

  // -------------------------------------------------------------------------
  // Failed
  // -------------------------------------------------------------------------
  if (phase === "failed") {
    return (
      <Reveal className="mx-auto flex max-w-md flex-col items-center py-16 text-center">
        <div className="grid size-14 place-items-center rounded-md border border-danger/40 bg-danger-subtle">
          <AlertCircle className="size-6 text-danger" />
        </div>
        <h1 className="type-display mt-6 text-3xl text-fg">Run didn&apos;t finish</h1>
        <p className="mt-3 text-pretty text-sm leading-relaxed text-fg-secondary">
          {error?.detail ?? "Something went wrong while tailoring your resume."}
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button size="lg" onClick={reset}>
            <Sparkles className="size-4" />
            Try again
          </Button>
          <ButtonLink href="/runs" variant="secondary">
            View runs
            <ArrowRight className="size-4" />
          </ButtonLink>
        </div>
      </Reveal>
    );
  }

  // -------------------------------------------------------------------------
  // Running — the wait-on-page progress view
  // -------------------------------------------------------------------------
  if (phase === "running") {
    const progress = run?.progress ?? 0;
    const stage = (run?.progress_stage ?? "queued") as RunStage;
    // Clamp for the bar; keep a little movement even at 0 so it never looks stuck.
    const barPct = Math.max(4, Math.min(progress, 100));

    return (
      <div className="mx-auto max-w-lg py-12">
        <Reveal className="flex flex-col items-center text-center">
          <div className="grid size-14 place-items-center rounded-md border border-accent/40 bg-accent-subtle">
            <Loader2 className="size-6 animate-spin text-accent-text" />
          </div>
          <h1 className="type-display mt-6 text-3xl text-fg">Tailoring your resume</h1>
          <p className="mt-3 text-pretty text-sm leading-relaxed text-fg-secondary">
            Hang tight — this usually takes a minute or two. Keep this tab open.
          </p>
        </Reveal>

        <Reveal delay={80} className="mt-10">
          {/* Progress bar */}
          <div className="flex items-center justify-between">
            <span className="font-mono text-2xs uppercase tracking-wide text-fg-tertiary">
              {STAGE_LABEL[stage]}
            </span>
            <span className="font-mono text-2xs font-medium tabular-nums text-fg-secondary">
              {progress}%
            </span>
          </div>
          <div
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface-sunken"
          >
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-700 ease-out"
              style={{ width: `${barPct}%` }}
            />
          </div>

          {/* Step checklist */}
          <ul className="mt-8 space-y-3">
            {STEPS.map((step, i) => {
              const next = STEPS[i + 1];
              const done = next ? progress >= next.at : progress >= 100;
              const active = !done && progress >= step.at;
              return (
                <li key={step.label} className="flex items-center gap-3">
                  <span
                    className={cn(
                      "grid size-6 shrink-0 place-items-center rounded-full border transition-colors",
                      done && "border-success/40 bg-success-subtle text-success",
                      active && "border-accent/40 bg-accent-subtle text-accent-text",
                      !done && !active && "border-border-default text-fg-quaternary",
                    )}
                  >
                    {done ? (
                      <CheckCircle2 className="size-4" />
                    ) : active ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <span className="size-1.5 rounded-full bg-current" />
                    )}
                  </span>
                  <span
                    className={cn(
                      "text-sm transition-colors",
                      done && "text-fg-secondary",
                      active && "font-medium text-fg",
                      !done && !active && "text-fg-quaternary",
                    )}
                  >
                    {step.label}
                  </span>
                </li>
              );
            })}
          </ul>

          <p className="mt-8 text-center font-mono text-2xs text-fg-quaternary">
            You can also leave and watch it on the{" "}
            <Link href="/runs" className="underline underline-offset-4 hover:text-fg">
              runs page
            </Link>
            .
          </p>
        </Reveal>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Form (default)
  // -------------------------------------------------------------------------
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <Reveal>
        <p className="eyebrow flex items-center gap-2">
          <span className="inline-block h-px w-6 bg-accent" />
          New run
        </p>
        <h1 className="type-display mt-3 text-3xl text-fg sm:text-4xl">Tailor a resume</h1>
        <p className="mt-2 text-sm text-fg-tertiary">
          Paste the job posting link. We read the posting, rewrite your resume for it, and score
          the result.
        </p>
      </Reveal>

      <Reveal delay={80}>
        <form onSubmit={submit} className="space-y-6">
          {/* Job posting URL */}
          <div className="space-y-2">
            <label htmlFor="jd_url" className="mono-label">
              Job posting URL
            </label>
            <div className="flex items-center gap-2 rounded-md border border-border-default bg-surface-sunken px-3.5 focus-within:border-fg-primary focus-within:ring-2 focus-within:ring-fg-primary/15">
              <Link2 className="size-4 shrink-0 text-fg-tertiary" aria-hidden="true" />
              <input
                id="jd_url"
                type="url"
                inputMode="url"
                required
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://company.com/careers/senior-engineer"
                className="w-full bg-transparent py-2.5 text-sm text-fg placeholder:text-fg-tertiary focus:outline-none"
              />
            </div>
            <p className="font-mono text-2xs text-fg-quaternary">
              Paste the direct link to the posting. Works with most job boards and career pages.
            </p>
          </div>

          {/* Optional metadata */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="company" label="Company" placeholder="Lexi" value={company} onChange={setCompany} />
            <Field id="role" label="Role" placeholder="AI Engineer" value={role} onChange={setRole} />
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-md border border-danger/40 bg-danger-subtle px-4 py-3 text-sm text-danger"
            >
              {error.detail}
              {needsOnboarding && (
                <>
                  {" "}
                  <Link href="/onboarding" className="font-medium underline">
                    Complete your profile
                  </Link>
                  .
                </>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-4 border-t border-border-subtle pt-6">
            <p className="font-mono text-2xs uppercase tracking-wide text-fg-quaternary">
              Uses 1 of your 3 free monthly resumes
            </p>
            <Button type="submit" size="lg" loading={loading} disabled={!canSubmit}>
              <Sparkles className="size-4" />
              {loading ? "Submitting…" : "Tailor resume"}
            </Button>
          </div>
        </form>
      </Reveal>
    </div>
  );
}

function Field({
  id,
  label,
  placeholder,
  value,
  onChange,
}: {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="flex items-center gap-1.5">
        <span className="mono-label">{label}</span>
        <span className="font-mono text-2xs lowercase text-fg-tertiary">optional</span>
      </label>
      <input
        id={id}
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-border-default bg-surface-sunken px-4 py-2.5 text-sm text-fg transition-colors placeholder:text-fg-tertiary focus:border-fg-primary focus:outline-none focus:ring-2 focus:ring-fg-primary/15"
      />
    </div>
  );
}
