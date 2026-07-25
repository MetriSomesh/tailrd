import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard",
  robots: { index: false, follow: false },
};

/**
 * App shell for authenticated routes (/dashboard, /tailor, /runs, /billing).
 * Marketing routes live in (marketing) group with their own layout.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      {/* Sticky header */}
      <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border-subtle bg-surface-base/80 px-6 backdrop-blur-md">
        <a href="/dashboard" className="text-base font-semibold tracking-tight text-fg">
          {SITE.name}
        </a>
        <nav className="flex items-center gap-1">
          <a href="/dashboard" className="rounded-md px-3 py-1.5 text-sm text-fg-secondary hover:bg-surface-raised hover:text-fg transition-colors">
            Dashboard
          </a>
          <a href="/tailor" className="rounded-md px-3 py-1.5 text-sm text-fg-secondary hover:bg-surface-raised hover:text-fg transition-colors">
            Tailor
          </a>
          <a href="/runs" className="rounded-md px-3 py-1.5 text-sm text-fg-secondary hover:bg-surface-raised hover:text-fg transition-colors">
            Runs
          </a>
          <a href="/billing" className="rounded-md px-3 py-1.5 text-sm text-fg-secondary hover:bg-surface-raised hover:text-fg transition-colors">
            Billing
          </a>
        </nav>
      </header>

      {/* Content */}
      <main id="main" className="flex-1 px-6 py-8">
        <div className="mx-auto w-full max-w-5xl">
          {children}
        </div>
      </main>
    </div>
  );
}
