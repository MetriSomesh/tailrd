import { Reveal } from "@/components/motion/reveal";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { ButtonLink } from "@/components/ui/button";
import { SITE } from "@/lib/site";
import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Briefcase, FileText, GraduationCap, Wrench } from "lucide-react";

export const metadata: Metadata = {
  title: "Get started",
  robots: { index: false, follow: false },
};

const steps = [
  { Icon: FileText, title: "Your basics", body: "Name, contact, and the summary line that opens every resume." },
  { Icon: GraduationCap, title: "Education", body: "Degrees and institutions. Kept exactly as you enter them." },
  { Icon: Briefcase, title: "Experience", body: "Roles and achievements. We rephrase these per job, never invent them." },
  { Icon: Wrench, title: "Skills & projects", body: "Your toolkit and work. Toggle whether AI may draft new projects." },
];

export default function OnboardingPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="container-page flex h-16 items-center justify-between">
        <Link href="/" className="text-base font-semibold tracking-tight text-fg">
          {SITE.name}
        </Link>
        <ThemeToggle />
      </header>

      <main id="main" className="container-page flex flex-1 items-center py-12">
        <div className="mx-auto w-full max-w-2xl">
          <Reveal>
            <p className="eyebrow">Welcome</p>
            <h1 className="type-display mt-3 text-fluid-h2 text-balance text-fg">
              Let&apos;s build your base resume
            </h1>
            <p className="mt-4 max-w-lg text-fg-secondary">
              Four short steps. Once it is saved, tailoring a resume for any job takes
              under a minute. You can edit everything later.
            </p>
          </Reveal>

          <Reveal delay={80}>
            <ol className="mt-10 space-y-px overflow-hidden rounded-2xl ring-1 ring-border-subtle">
              {steps.map(({ Icon, title, body }, i) => (
                <li
                  key={title}
                  className="flex items-start gap-4 bg-surface-raised p-5"
                >
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-accent-subtle ring-1 ring-inset ring-accent/15">
                    <Icon className="size-4 text-accent" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-baseline gap-2">
                      <span className="font-mono text-2xs tabular-nums text-fg-quaternary">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <h2 className="text-sm font-medium text-fg">{title}</h2>
                    </div>
                    <p className="mt-1 text-sm text-fg-tertiary">{body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Reveal>

          <Reveal delay={160}>
            <div className="mt-8 flex items-center gap-3">
              <ButtonLink href="/dashboard" size="lg">
                Start setup
                <ArrowRight className="size-4" />
              </ButtonLink>
              <ButtonLink href="/dashboard" variant="ghost" size="lg">
                Skip for now
              </ButtonLink>
            </div>
          </Reveal>
        </div>
      </main>
    </div>
  );
}
