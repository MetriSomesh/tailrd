"use client";

import { Reveal } from "@/components/motion/reveal";
import { Button, ButtonLink } from "@/components/ui/button";
import { ApiRequestError, submitTailor } from "@/lib/api";
import { cn } from "@/lib/cn";
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const MIN_JD = 50;

interface SubmitError {
  detail: string;
  code: string;
}

export default function TailorPage() {
  const [jd, setJd] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<SubmitError | null>(null);

  const remaining = MIN_JD - jd.trim().length;
  const canSubmit = remaining <= 0 && !loading;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      await submitTailor({
        jd_text: jd,
        company: company.trim() || undefined,
        role: role.trim() || undefined,
      });
      setDone(true);
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

  if (done) {
    return (
      <Reveal className="mx-auto flex max-w-md flex-col items-center py-20 text-center">
        <div className="grid size-14 place-items-center rounded-md border border-success/40 bg-success-subtle">
          <CheckCircle2 className="size-6 text-success" />
        </div>
        <h1 className="type-display mt-6 text-3xl text-fg">Queued</h1>
        <p className="mt-3 text-pretty text-sm leading-relaxed text-fg-secondary">
          Your resume is being tailored. It usually takes under a minute. The scored DOCX and
          gap report will be waiting on the runs page.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <ButtonLink href="/runs">
            Watch progress
            <ArrowRight className="size-4" />
          </ButtonLink>
          <Button
            variant="secondary"
            onClick={() => {
              setDone(false);
              setJd("");
              setCompany("");
              setRole("");
            }}
          >
            Tailor another
          </Button>
        </div>
      </Reveal>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <Reveal>
        <p className="eyebrow flex items-center gap-2">
          <span className="inline-block h-px w-6 bg-accent" />
          New run
        </p>
        <h1 className="type-display mt-3 text-3xl text-fg sm:text-4xl">Tailor a resume</h1>
        <p className="mt-2 text-sm text-fg-tertiary">
          Paste the posting. We rewrite your resume for it and score the result.
        </p>
      </Reveal>

      <Reveal delay={80}>
        <form onSubmit={submit} className="space-y-6">
          {/* JD */}
          <div className="rounded-md border border-border-default bg-surface-raised">
            <div className="flex items-baseline justify-between gap-3 border-b border-border-subtle px-5 py-3">
              <label htmlFor="jd" className="mono-label">
                Job description
              </label>
              <span
                className={cn(
                  "font-mono text-2xs tabular-nums",
                  remaining > 0 ? "text-fg-quaternary" : "text-accent-text",
                )}
              >
                {remaining > 0 ? `${remaining} more characters` : `${jd.trim().length} characters`}
              </span>
            </div>

            <textarea
              id="jd"
              rows={14}
              required
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder={"Paste the full posting here: responsibilities, requirements, everything.\n\nThe more complete it is, the more accurate the score."}
              className="w-full resize-y rounded-b-md bg-surface-raised px-5 py-4 text-sm leading-relaxed text-fg transition-colors placeholder:text-fg-tertiary focus:outline-none focus:ring-0"
            />
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
              {loading ? "Tailoring…" : "Tailor resume"}
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
