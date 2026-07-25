import { SITE } from "@/lib/site";
import Link from "next/link";

/**
 * Marketing layout — used by /, /pricing, /terms, /privacy, /refund-policy, /contact.
 * These pages are public, SEO-indexed, and have their own minimal nav/footer.
 */
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      {/* Minimal marketing header */}
      <header className="flex h-14 items-center justify-between px-6 lg:px-12">
        <Link href="/" className="text-base font-semibold tracking-tight text-fg">
          {SITE.name}
        </Link>
        <nav className="flex items-center gap-4">
          <a href="/pricing" className="text-sm text-fg-secondary hover:text-fg transition-colors">
            Pricing
          </a>
          <a
            href="/login"
            className="rounded-lg bg-accent px-4 py-1.5 text-sm font-medium text-accent-contrast hover:bg-accent-hover transition-colors"
          >
            Sign in
          </a>
        </nav>
      </header>

      {/* Page content */}
      <main id="main" className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-border-subtle px-6 py-10 lg:px-12">
        <div className="mx-auto flex max-w-5xl flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-fg-quaternary">&copy; {new Date().getFullYear()} {SITE.legalEntity}. All rights reserved.</p>
          <nav className="flex flex-wrap gap-4 text-xs text-fg-tertiary">
            <a href="/terms" className="hover:text-fg transition-colors">Terms</a>
            <a href="/privacy" className="hover:text-fg transition-colors">Privacy</a>
            <a href="/refund-policy" className="hover:text-fg transition-colors">Refund Policy</a>
            <a href="/contact" className="hover:text-fg transition-colors">Contact</a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
