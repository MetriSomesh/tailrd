"use client";

import { Reveal } from "@/components/motion/reveal";
import { Button, ButtonLink } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import { useState } from "react";

const MIN_JD = 50;

export default function TailorPage() {
  const [jd, setJd] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const remaining = MIN_JD - jd.trim().length;
  const canSubmit = remaining <= 0 && !loading;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    // TODO: POST /api/backend/tailor
    await new Promise((r) => setTimeout(r, 1400));
    setLoading(false);
    setDone(true);
  }

  if (done) {
    return (
      <Reveal className="mx-auto flex max-w-md flex-col items-center py-20 text-center">
        <div className="grid size-14 place-items-center rounded-2xl bg-success-subtle ring-1 ring-inset ring-success/20">
          <CheckCircle2 className="size-6 text-success" />
        </div>
        <h1 className="type-display mt-6 text-3xl text-fg">Queued</h1>
        <p className="mt-3 text-pretty text-sm leading-relaxed text-fg-secondary">
          Your resume is being tailored. It usually takes under a minute — we will have the
          scored DOCX and gap report waiting on the runs page.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <ButtonLink href="/runs">
            Watch progress
            <ArrowRight className="size-4" />
          </ButtonLink>
          <Button variant="secondary" onClick={() => {
            setDone(false);
            setJd("");
            setCompany("");
            setRole("");
          }}>
            Tailor another
          </Button>
        </div>
      </Reveal>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <Reveal>
        <h1 className="type-display text-3xl text-fg sm:text-4xl">Tailor a resume</h1>
        <p className="mt-2 text-sm text-fg-tertiary">
          Paste the posting. We rewrite your resume for it and score the result.
        </p>
      </Reveal>

      <Reveal delay={80}>
        <form onSubmit={submit} className="space-y-6">
          {/* JD */}
          <div className="hairline-top rounded-2xl bg-surface-raised p-5 ring-1 ring-border-subtle sm:p-6">
            <div className="flex items-baseline justify-between gap-3">
              <label htmlFor="jd" className="text-sm font-medium text-fg">
                Job description
              </label>
              <span
                className={cn(
                  "font-mono text-2xs tabular-nums",
                  remaining > 0 ? "text-fg-quaternary" : "text-success",
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
              placeholder={"Paste the full posting here — responsibilities, requirements, everything.\n\nThe more complete it is, the more accurate the score."}
              className="mt-3 w-full resize-y rounded-xl border border-border-default bg-surface-sunken px-4 py-3.5 text-sm leading-relaxed text-fg transition-colors placeholder:text-fg-tertiary focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/12"
            />
          </div>

          {/* Optional metadata */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              id="company"
              label="Company"
              placeholder="Lexi"
              value={company}
              onChange={setCompany}
            />
            <Field
              id="role"
              label="Role"
              placeholder="AI Engineer"
              value={role}
              onChange={setRole}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-xs text-fg-quaternary">Uses 1 of your 3 free monthly resumes.</p>
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
      <label htmlFor={id} className="text-sm font-medium text-fg">
        {label}
        <span className="ml-1.5 text-2xs font-normal text-fg-quaternary">optional</span>
      </label>
      <input
        id={id}
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-border-default bg-surface-sunken px-4 py-2.5 text-sm text-fg transition-colors placeholder:text-fg-tertiary focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/12"
      />
    </div>
  );
}
