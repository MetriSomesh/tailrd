import { Button } from "@/components/ui/button";
import { AppJsonLd } from "@/components/seo/json-ld";
import { ArrowRight, FileCheck, Target, Zap } from "lucide-react";

/**
 * Landing page — the first thing a visitor sees.
 *
 * Anti-slop: no gradient hero, no 3D blobs, no "Supercharge your X with AI".
 * Instrument Serif headline, clear value prop, immediate CTA.
 */
export default function LandingPage() {
  return (
    <>
      <AppJsonLd />

      {/* Hero */}
      <section className="mx-auto max-w-4xl px-6 py-24 text-center lg:py-32">
        <p className="eyebrow mb-5">AI resume tailoring</p>
        <h1 className="display text-5xl text-fg leading-none sm:text-6xl lg:text-7xl">
          Resumes that clear<br className="hidden sm:block" /> the filter
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg text-fg-secondary leading-relaxed">
          Paste a job description. Get back a resume rewritten to match it, scored against
          real ATS criteria, with every gap called out so you know exactly where you stand.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <a href="/signup">
            <Button size="lg">
              Start for free
              <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
          <a href="/pricing">
            <Button variant="secondary" size="lg">
              See pricing
            </Button>
          </a>
        </div>
        <p className="mt-4 text-xs text-fg-quaternary">3 free resumes per month. No credit card.</p>
      </section>

      {/* Value props */}
      <section className="border-t border-border-subtle py-20">
        <div className="mx-auto grid max-w-5xl gap-12 px-6 sm:grid-cols-3">
          <div className="space-y-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-subtle">
              <Target className="h-5 w-5 text-accent" />
            </div>
            <h3 className="text-base font-medium text-fg">JD-aware scoring</h3>
            <p className="text-sm text-fg-secondary leading-relaxed">
              Skills, keywords, and responsibilities are extracted from the JD itself — not
              a generic checklist. You see exactly which requirements are covered and which aren&apos;t.
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-subtle">
              <FileCheck className="h-5 w-5 text-accent" />
            </div>
            <h3 className="text-base font-medium text-fg">ATS-validated DOCX</h3>
            <p className="text-sm text-fg-secondary leading-relaxed">
              Every generated resume is checked for parsability — we verify that ATS systems can
              actually extract the content, not just that it looks good to a human.
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-subtle">
              <Zap className="h-5 w-5 text-accent" />
            </div>
            <h3 className="text-base font-medium text-fg">Gap analysis, not magic</h3>
            <p className="text-sm text-fg-secondary leading-relaxed">
              No vague &ldquo;your resume is 72% ready&rdquo;. You get the specific responsibilities
              uncovered, the skills missing, and the keywords to add — actionable, not decorative.
            </p>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border-subtle py-20">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <p className="eyebrow mb-4">How it works</p>
          <h2 className="display text-3xl text-fg sm:text-4xl">Three steps. One minute.</h2>
        </div>
        <div className="mx-auto mt-12 grid max-w-4xl gap-8 px-6 sm:grid-cols-3">
          {[
            { step: "1", title: "Paste the JD", desc: "Copy the job description from any posting." },
            { step: "2", title: "AI tailors your resume", desc: "Rewrites bullets, reorders skills, fills gaps — in under a minute." },
            { step: "3", title: "Download + review", desc: "Get a scored DOCX with a gap report. Edit anything before sending." },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-surface-raised text-sm font-semibold text-fg ring-1 ring-border-default">
                {item.step}
              </span>
              <h3 className="mt-4 text-sm font-medium text-fg">{item.title}</h3>
              <p className="mt-2 text-sm text-fg-tertiary">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="border-t border-border-subtle py-20 text-center">
        <h2 className="display text-3xl text-fg">Ready to stop guessing?</h2>
        <p className="mx-auto mt-3 max-w-md text-fg-secondary">
          Three free resumes per month. No credit card required. No commitment.
        </p>
        <a href="/signup" className="mt-8 inline-block">
          <Button size="lg">
            Get started free
            <ArrowRight className="h-4 w-4" />
          </Button>
        </a>
      </section>
    </>
  );
}
