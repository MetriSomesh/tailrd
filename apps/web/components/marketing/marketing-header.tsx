"use client";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { ButtonLink } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { SITE } from "@/lib/site";
import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

const navLinks = [{ href: "/pricing", label: "Pricing" }];

export function MarketingHeader() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // Condense the header once the user scrolls past the fold edge.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Lock the page while the mobile sheet is open.
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 border-b transition-[background-color,border-color,backdrop-filter] duration-normal",
        scrolled
          ? "border-border-strong bg-surface-base/85 backdrop-blur-xl"
          : "border-border-subtle bg-surface-base",
      )}
    >
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <Link
          href="/"
          className="group flex items-center gap-2.5 transition-opacity hover:opacity-80"
        >
          <span aria-hidden="true" className="size-3 rounded-[2px] bg-accent" />
          <span className="type-display text-lg tracking-tight text-fg">{SITE.name}</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden items-center gap-1 sm:flex">
          <nav aria-label="Main" className="flex items-center">
            {navLinks.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="rounded-md px-3 py-1.5 font-mono text-2xs uppercase tracking-wide text-fg-secondary transition-colors hover:text-fg"
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <ThemeToggle className="ml-2" />
          <ButtonLink href="/login" size="sm" variant="ghost" className="ml-2">
            Sign in
          </ButtonLink>
          <ButtonLink href="/signup" size="sm">
            Get started
          </ButtonLink>
        </div>

        {/* Mobile trigger */}
        <div className="flex items-center gap-2 sm:hidden">
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
            className="grid size-9 place-items-center rounded-md text-fg-secondary border border-border-default transition-colors hover:bg-surface-raised hover:text-fg"
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>

      {/* Mobile sheet */}
      <div
        id="mobile-nav"
        hidden={!open}
        className="border-t border-border-strong bg-surface-base px-5 pb-6 pt-4 sm:hidden"
      >
        <nav aria-label="Mobile" className="flex flex-col">
          {navLinks.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="border-b border-border-subtle px-1 py-3 font-mono text-xs uppercase tracking-wide text-fg-secondary transition-colors hover:text-fg"
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="mt-4 flex flex-col gap-2">
          <ButtonLink href="/login" variant="secondary" className="w-full">
            Sign in
          </ButtonLink>
          <ButtonLink href="/signup" className="w-full">
            Get started
          </ButtonLink>
        </div>
      </div>
    </header>
  );
}
