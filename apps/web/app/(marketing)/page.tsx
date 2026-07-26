import { ScorePreview } from "@/components/marketing/score-preview";
import { Reveal } from "@/components/motion/reveal";
import { AppJsonLd } from "@/components/seo/json-ld";
import { ButtonLink } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { ArrowRight, FileCheck, Target, Zap } from "lucide-react";

const metaStrip = [
  { k: "Free tier", v: "3 / month" },
  { k: "Output", v: "ATS-ready DOCX" },
  { k: "Scoring", v: "JD-aware" },
  { k: "Setup", v: "~60 seconds" },
];

const features = [
  {
    Icon: Target,
    tag: "01",
    title: "JD-aware scoring",
    body: "Skills, keywords and responsibilities are extracted from the posting itself, not matched against a generic checklist. You see which requirements you cover and which you do not.",
  },
  {
    Icon: FileCheck,
    tag: "02",
    title: "Parsability-validated",
    body: "Every DOCX is text-extracted and re-checked before you get it, so an ATS can actually read it. Looking right to a human is not the same as parsing correctly.",
  },
  {
    Icon: Zap,
    tag: "03",
    title: "Gaps, not vibes",
    body: "No vague readiness percentage. You get the specific uncovered responsibilities, the missing skills, and the keywords worth adding.",
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
      <section className="relative overflow-hidden border-b border-border-strong">
        <div aria-hidden="true" className="bg-ruled absolute inset-0 -z-10 opacity-70" />

        <div className="container-page grid items-center gap-12 py-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.02fr)] lg:gap-16 lg:py-24">
          {/* Copy column */}
          <div className="max-w-xl">
            <Reveal>
              <p className="eyebrow flex items-center gap-2">
                <span className="inline-block h-px w-6 bg-accent" />
                ATS resume engine
              </p>
            </Reveal>

            <Reveal delay={60}>
              <h1 className="type-display mt-5 text-fluid-hero text-fg">
                Resumes that{" "}
                <br />
                clear the{" "}
                <span
                  className="box-decoration-clone px-1"
                  style={{
                    backgroundImage:
                      "linear-gradient(to top, var(--accent) 0.16em, transparent 0.16em)",
                  }}
                >
                  filter
                </span>
              </h1>
            </Reveal>

            <Reveal delay={120}>
              <p className="mt-8 max-w-md text-fluid-lead text-pretty text-fg-secondary">
                Paste a job description. Get back a resume rewritten for that role, scored
                against real ATS criteria, with every unmet requirement named.
              </p>
            </Reveal>

            <Reveal delay={180}>
              <div className="mt-9 flex flex-wrap gap-3">
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
              <p className="mt-4 font-mono text-2xs uppercase tracking-wide text-fg-quaternary">
                No credit card · No trial countdown
              </p>
            </Reveal>
          </div>

          {/* Visual column */}
          <Reveal delay={200}>
            <ScorePreview />
          </Reveal>
        </div>
      </section>

      {/* --------------------------------------------------------- Meta strip */}
      <section className="border-b border-border-strong">
        <div className="container-page grid grid-cols-2 divide-x divide-y divide-border-subtle border-x border-border-subtle sm:grid-cols-4 sm:divide-y-0">
          {metaStrip.map((m) => (
            <div key={m.k} className="px-5 py-6">
              <p className="mono-label">{m.k}</p>
              <p className="type-display mt-2 text-xl text-fg">{m.v}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------ Features */}
      <section className="border-b border-border-strong">
        <div className="container-page py-18 lg:py-24">
          <Reveal>
            <p className="eyebrow">Why it scores differently</p>
            <h2 className="type-display mt-4 max-w-3xl text-fluid-h2 text-balance text-fg">
              Most checkers grade against a template. This one grades against the job.
            </h2>
          </Reveal>

          {/* Bento: a tall accent anchor, two features, then one wide feature.
              Spans are arranged so the 3-column grid fills with no empty cells. */}
          <div className="mt-12 grid gap-px overflow-hidden rounded-md border border-border-strong bg-border-subtle lg:grid-cols-3 lg:grid-rows-2">
            <Reveal className="flex flex-col justify-center bg-accent p-7 lg:row-span-2">
              <p className="font-mono text-2xs uppercase tracking-widest text-accent-contrast/70">
                Median lift
              </p>
              <p className="type-display mt-3 text-6xl text-accent-contrast">+31</p>
              <p className="mt-4 max-w-xs text-sm leading-snug text-accent-contrast/80">
                points of ATS score after one tailoring pass, across our test set.
              </p>
            </Reveal>

            {features.map(({ Icon, tag, title, body }, i) => (
              <Reveal
                key={title}
                delay={i * 80}
                className={cn("group bg-surface-base p-7", i === 2 && "lg:col-span-2")}
              >
                <div className="flex items-center justify-between">
                  <div className="flex size-9 items-center justify-center rounded-md border border-border-default text-fg transition-colors group-hover:border-border-strong">
                    <Icon className="size-4" />
                  </div>
                  <span className="font-mono text-2xs tabular-nums text-fg-quaternary">{tag}</span>
                </div>
                <h3 className="mt-5 text-base font-semibold text-fg">{title}</h3>
                <p className="mt-2.5 max-w-prose text-sm leading-relaxed text-fg-secondary">{body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------- How it works */}
      <section className="border-b border-border-strong bg-surface-sunken">
        <div className="container-page py-18 lg:py-24">
          <Reveal>
            <p className="eyebrow">How it works</p>
            <h2 className="type-display mt-4 text-fluid-h2 text-fg">
              Three steps, about a minute.
            </h2>
          </Reveal>

          <ol className="mt-12 border-t border-border-strong">
            {steps.map((s, i) => (
              <Reveal
                as="li"
                key={s.n}
                delay={i * 90}
                className="group grid grid-cols-[auto_1fr] items-center gap-x-6 gap-y-1 border-b border-border-subtle py-7 sm:grid-cols-[6rem_1fr_2fr] sm:gap-x-10"
              >
                <span className="type-display text-4xl leading-none text-fg-quaternary transition-colors group-hover:text-accent-text sm:text-5xl">
                  {s.n}
                </span>
                <h3 className="text-lg font-semibold text-fg">{s.title}</h3>
                <p className="col-start-2 text-sm leading-relaxed text-fg-tertiary sm:col-start-3">
                  {s.body}
                </p>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* ------------------------------------------------------------ Final CTA */}
      <section className="container-page py-18 lg:py-24">
        <Reveal>
          <div className="relative overflow-hidden rounded-md border border-border-strong bg-surface-inverse px-6 py-14 hard-shadow sm:px-12 lg:py-20">
            <div className="mx-auto flex max-w-2xl flex-col items-center text-center">
              <p className="mono-label text-fg-inverse/60">Get started</p>
              <h2 className="type-display mt-4 text-fluid-h2 text-balance text-fg-inverse">
                Stop guessing what the filter wants
              </h2>
              <p className="mt-5 max-w-md text-pretty text-fg-inverse/70">
                Three tailored resumes a month, free. Scored, validated, and honest about what is
                still missing.
              </p>
              <div className="mt-9">
                <ButtonLink href="/signup" size="lg">
                  Get started free
                  <ArrowRight className="size-4" />
                </ButtonLink>
              </div>
            </div>
          </div>
        </Reveal>
      </section>
    </>
  );
}
