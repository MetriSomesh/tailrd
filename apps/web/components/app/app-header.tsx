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
    <header className="sticky top-0 z-50 border-b border-border-subtle bg-surface-base/85 backdrop-blur-xl">
      <div className="container-page flex h-16 items-center gap-4">
        <Link href="/dashboard" className="text-base font-semibold tracking-tight text-fg">
          {SITE.name}
        </Link>

        {/* Desktop nav — pill-style active state */}
        <nav aria-label="Main" className="ml-4 hidden items-center gap-0.5 md:flex">
          {nav.map(({ href, label, Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors duration-fast",
                  active
                    ? "bg-surface-raised font-medium text-fg ring-1 ring-inset ring-border-subtle"
                    : "text-fg-tertiary hover:bg-surface-raised/60 hover:text-fg-secondary",
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
            className="grid size-9 place-items-center rounded-lg text-fg-secondary ring-1 ring-inset ring-border-subtle transition-colors hover:bg-surface-raised hover:text-fg md:hidden"
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>

      {/* Mobile nav */}
      <div
        id="app-mobile-nav"
        hidden={!open}
        className="border-t border-border-subtle bg-surface-base px-5 pb-5 pt-3 md:hidden"
      >
        <nav aria-label="Mobile" className="flex flex-col gap-0.5">
          {nav.map(({ href, label, Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-colors",
                  active
                    ? "bg-surface-raised font-medium text-fg"
                    : "text-fg-secondary hover:bg-surface-raised/60",
                )}
              >
                <Icon className="size-4" aria-hidden="true" />
                {label}
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
