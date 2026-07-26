"use client";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { ButtonLink } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { SITE } from "@/lib/site";
import { FileText, LayoutDashboard, Menu, Sparkles, Wallet, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const nav = [
  { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { href: "/tailor", label: "Tailor", Icon: Sparkles },
  { href: "/runs", label: "Runs", Icon: FileText },
  { href: "/billing", label: "Billing", Icon: Wallet },
];

export function AppHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <header className="sticky top-0 z-50 border-b border-border-strong bg-surface-base/85 backdrop-blur-xl">
      <div className="container-page flex h-16 items-center gap-4">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <span aria-hidden="true" className="size-3 rounded-[2px] bg-accent" />
          <span className="type-display text-lg tracking-tight text-fg">{SITE.name}</span>
        </Link>

        {/* Desktop nav — underline active state, mono labels */}
        <nav aria-label="Main" className="ml-6 hidden items-center gap-1 md:flex">
          {nav.map(({ href, label, Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2 border-b-2 px-2.5 py-1.5 font-mono text-2xs uppercase tracking-wide transition-colors duration-fast -mb-px",
                  active
                    ? "border-accent text-fg"
                    : "border-transparent text-fg-tertiary hover:text-fg",
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <ButtonLink href="/tailor" size="sm" className="hidden sm:inline-flex">
            <Sparkles className="size-3.5" />
            New resume
          </ButtonLink>
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="app-mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
            className="grid size-9 place-items-center rounded-md text-fg-secondary border border-border-default transition-colors hover:bg-surface-raised hover:text-fg md:hidden"
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>

      {/* Mobile nav */}
      <div
        id="app-mobile-nav"
        hidden={!open}
        className="border-t border-border-strong bg-surface-base px-5 pb-5 pt-2 md:hidden"
      >
        <nav aria-label="Mobile" className="flex flex-col">
          {nav.map(({ href, label, Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 border-b border-border-subtle px-1 py-3 font-mono text-xs uppercase tracking-wide transition-colors",
                  active ? "text-fg" : "text-fg-secondary hover:text-fg",
                )}
              >
                <Icon className="size-4 shrink-0" aria-hidden="true" />
                {label}
                {active && <span aria-hidden="true" className="ml-auto size-1.5 rounded-full bg-accent" />}
              </Link>
            );
          })}
        </nav>
        <ButtonLink href="/tailor" className="mt-4 w-full">
          <Sparkles className="size-4" />
          New resume
        </ButtonLink>
      </div>
    </header>
  );
}
