import { ScorePreview } from "@/components/marketing/score-preview";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { SITE } from "@/lib/site";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

/**
 * Split auth shell: form on the left, a branded proof panel on the right.
 * The right panel collapses away below lg so mobile gets a focused single column.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      {/* Form side */}
      <div className="flex flex-col">
        <header className="container-page flex h-16 items-center justify-between">
          <Link href="/" className="text-base font-semibold tracking-tight text-fg">
            {SITE.name}
          </Link>
          <ThemeToggle />
        </header>

        <main id="main" className="flex flex-1 items-center justify-center px-6 py-10">
          <div className="w-full max-w-sm">{children}</div>
        </main>
      </div>

      {/* Proof side — hidden on small screens */}
      <aside className="relative hidden overflow-hidden border-l border-border-subtle bg-surface-sunken/50 lg:block">
        <div aria-hidden="true" className="bg-grid absolute inset-0" />
        <div
          aria-hidden="true"
          className="glow-accent size-[32rem] -right-40 top-1/3"
        />
        <div className="relative flex h-full flex-col justify-center px-12 xl:px-20">
          <p className="eyebrow">What you get</p>
          <h2 className="type-display mt-3 text-3xl text-balance text-fg">
            A score you can act on, not a vanity metric.
          </h2>
          <div className="mt-10 max-w-md">
            <ScorePreview />
          </div>
        </div>
      </aside>
    </div>
  );
}
