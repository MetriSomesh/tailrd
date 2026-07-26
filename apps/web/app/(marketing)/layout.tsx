import { MarketingHeader } from "@/components/marketing/marketing-header";
import { SITE } from "@/lib/site";
import Link from "next/link";

const footerLinks = [
  { href: "/pricing", label: "Pricing" },
  { href: "/terms", label: "Terms" },
  { href: "/privacy", label: "Privacy" },
  { href: "/refund-policy", label: "Refunds" },
  { href: "/contact", label: "Contact" },
];

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <MarketingHeader />

      <main id="main" className="flex-1">
        {children}
      </main>

      <footer className="border-t border-border-strong">
        <div className="container-page flex flex-col gap-6 py-10 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2.5">
            <span aria-hidden="true" className="size-3 rounded-[2px] bg-accent" />
            <div>
              <p className="type-display text-base tracking-tight text-fg">{SITE.name}</p>
              <p className="mt-0.5 font-mono text-2xs uppercase tracking-wide text-fg-quaternary">
                &copy; {new Date().getFullYear()} {SITE.legalEntity}
              </p>
            </div>
          </div>
          <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-2">
            {footerLinks.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="font-mono text-2xs uppercase tracking-wide text-fg-tertiary transition-colors hover:text-fg"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
      </footer>
    </div>
  );
}
