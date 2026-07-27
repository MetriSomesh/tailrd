"use client";

import { Reveal } from "@/components/motion/reveal";
import { Button, ButtonLink } from "@/components/ui/button";
import { ApiRequestError, submitTailor } from "@/lib/api";
import { ArrowRight, CheckCircle2, Link2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

interface SubmitError {
  detail: string;
  code: string;
}

const URL_RE = /^https?:\/\/\S+\.\S+/i;

export default function TailorPage() {
  const [url, setUrl] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<SubmitError | null>(null);

  const validUrl = URL_RE.test(url.trim());
  const canSubmit = validUrl && !loading;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      await submitTailor({
        jd_url: url.trim(),
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
          We&apos;re reading the posting and tailoring your resume — this takes a minute or two.
          The scored DOCX and gap report will be waiting on the runs page.
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
              setUrl("");
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
