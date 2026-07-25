import { ScorePreview } from "@/components/marketing/score-preview";
import { Reveal } from "@/components/motion/reveal";
import { AppJsonLd } from "@/components/seo/json-ld";
import { ButtonLink } from "@/components/ui/button";
import { ArrowRight, FileCheck, Target, Zap } from "lucide-react";

const features = [
  {
    Icon: Target,
    title: "JD-aware scoring",
    body: "Skills, keywords and responsibilities are extracted from the posting itself, not matched against a generic checklist. You see which requirements you cover and which you do not.",
  },
  {
    Icon: FileCheck,
    title: "Parsability-validated",
    body: "Every DOCX is text-extracted and re-checked before you get it, so an ATS can actually read the content. Looking right to a human is not the same as parsing correctly.",
  },
  {
    Icon: Zap,
    title: "Gaps, not vibes",
    body: "No vague readiness percentage. You get the specific uncovered responsibilities, the missing skills, and the keywords worth adding, each one actionable.",
  },
];

const steps = [
  { n: "01", title: "Paste the posting", body: "Any job description. No formatting needed." },
  { n: "02", title: "We rewrite and score", body: "Bullets, skills and summary, tuned to that role." },
  { n: "03", title: "Review the gaps", body: "Download the DOCX, fix what is flagged, send it." },
];

export default function LandingPage() {
  return (
    <>
      <AppJsonLd />

      {/* ---------------------------------------------------------------- Hero */}
      <section className="relative overflow-hidden">
        {/* Backdrop: faint engineering grid + one accent glow. No gradient wash. */}
        <div aria-hidden="true" className="bg-grid absolute inset-0 -z-10" />
        <div
          aria-hidden="true"
          className="glow-accent -z-10 size-[36rem] -top-40 left-1/2 -translate-x-1/2"
        />

        <div className="container-page grid items-center gap-14 py-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-16 lg:py-28">
          {/* Copy column — left-aligned on desktop, centred on mobile */}
          <div className="mx-auto max-w-xl text-center lg:mx-0 lg:text-left">
            <Reveal>
              <span className="inline-flex items-center gap-2 rounded-full bg-surface-raised px-3 py-1 ring-1 ring-inset ring-border-subtle">
                <span className="relative flex size-1.5">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-accent opacity-60" />
                  <span className="relative inline-flex size-1.5 rounded-full bg-accent" />
                </span>
                <span className="text-2xs font-medium tracking-wide text-fg-secondary">
                  3 free resumes every month
                </span>
              </span>
            </Reveal>

            <Reveal delay={60}>
              <h1 className="type-display mt-6 text-fluid-hero text-balance text-fg">
                Resumes that clear the filter
              </h1>
            </Reveal>

            <Reveal delay={120}>
              <p className="mt-6 text-fluid-lead text-pretty text-fg-secondary">
                Paste a job description. Get back a resume rewritten for that role, scored
                against real ATS criteria, with every unmet requirement named.
              </p>
            </Reveal>

            <Reveal delay={180}>
              <div className="mt-9 flex flex-wrap justify-center gap-3 lg:justify-start">
                <ButtonLink href="/signup" size="lg">
                  Start for free
                  <ArrowRight className="size-4" />
                </ButtonLink>
                <ButtonLink href="/pricing" variant="secondary" size="lg">
                  See pricing
                </ButtonLink>
              </div>
            </Reveal>

            <Reveal delay={240}>
              <p className="mt-4 text-xs text-fg-quaternary">
                No credit card. No trial countdown.
              </p>
            </Reveal>
          </div>

          {/* Visual column */}
          <Reveal delay={200} className="lg:pl-4">
            <ScorePreview />
          </Reveal>
        </div>
      </section>

      {/* ------------------------------------------------------------ Features */}
      <section className="border-t border-border-subtle">
        <div className="container-page py-20 lg:py-24">
          <Reveal>
            <p className="eyebrow">Why it scores differently</p>
            <h2 className="type-display mt-3 max-w-2xl text-fluid-h2 text-balance text-fg">
              Most checkers grade against a template. This one grades against the job.
            </h2>
          </Reveal>

          <div className="mt-14 grid gap-x-10 gap-y-12 sm:grid-cols-2 lg:grid-cols-3">
            {features.map(({ Icon, title, body }, i) => (
              <Reveal key={title} delay={i * 80} className="group">
                <div className="flex size-10 items-center justify-center rounded-xl bg-accent-subtle ring-1 ring-inset ring-accent/15 transition-transform duration-normal group-hover:-translate-y-0.5">
                  <Icon className="size-4.5 text-accent" />
                </div>
                <h3 className="mt-5 text-base font-medium text-fg">{title}</h3>
                <p className="mt-2.5 text-sm leading-relaxed text-fg-secondary">{body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------- How it works */}
      <section className="border-t border-border-subtle bg-surface-sunken/40">
        <div className="container-page py-20 lg:py-24">
          <Reveal>
            <p className="eyebrow">How it works</p>
            <h2 className="type-display mt-3 text-fluid-h2 text-fg">Three steps, about a minute.</h2>
          </Reveal>

          {/* Numbered rows, not cramped columns — reads cleanly at every width */}
          <ol className="mt-12 grid gap-px overflow-hidden rounded-2xl bg-border-subtle sm:grid-cols-3">
            {steps.map((s, i) => (
              <Reveal as="li" key={s.n} delay={i * 90} className="bg-surface-base p-6 sm:p-7">
                <span className="font-mono text-2xs tabular-nums text-accent">{s.n}</span>
                <h3 className="mt-3 text-base font-medium text-fg">{s.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-fg-tertiary">{s.body}</p>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* ------------------------------------------------------------ Final CTA */}
      <section className="relative overflow-hidden border-t border-border-subtle">
        <div
          aria-hidden="true"
          className="glow-accent -z-10 size-[28rem] -bottom-56 left-1/2 -translate-x-1/2"
        />
        <div className="container-page py-24 text-center lg:py-28">
          <Reveal>
            <h2 className="type-display mx-auto max-w-2xl text-fluid-h2 text-balance text-fg">
              Stop guessing what the filter wants
            </h2>
            <p className="mx-auto mt-5 max-w-md text-pretty text-fg-secondary">
              Three tailored resumes a month, free. Scored, validated, and honest about
              what is still missing.
            </p>
            <div className="mt-9 flex justify-center">
              <ButtonLink href="/signup" size="lg">
                Get started free
                <ArrowRight className="size-4" />
              </ButtonLink>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
