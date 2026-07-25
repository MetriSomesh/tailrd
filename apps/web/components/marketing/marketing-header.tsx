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
        "sticky top-0 z-50 transition-[background-color,border-color,backdrop-filter] duration-normal",
        scrolled
          ? "border-b border-border-subtle bg-surface-base/80 backdrop-blur-xl"
          : "border-b border-transparent",
      )}
    >
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <Link
          href="/"
          className="text-base font-semibold tracking-tight text-fg transition-opacity hover:opacity-80"
        >
          {SITE.name}
        </Link>

        {/* Desktop nav */}
        <div className="hidden items-center gap-2 sm:flex">
          <nav aria-label="Main" className="flex items-center">
            {navLinks.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="rounded-lg px-3 py-1.5 text-sm text-fg-secondary transition-colors hover:bg-surface-raised hover:text-fg"
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <ThemeToggle className="ml-1" />
          <ButtonLink href="/login" size="sm" variant="secondary" className="ml-1">
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
            className="grid size-9 place-items-center rounded-lg text-fg-secondary ring-1 ring-inset ring-border-subtle transition-colors hover:bg-surface-raised hover:text-fg"
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>

      {/* Mobile sheet */}
      <div
        id="mobile-nav"
        hidden={!open}
        className="border-t border-border-subtle bg-surface-base px-5 pb-6 pt-4 sm:hidden"
      >
        <nav aria-label="Mobile" className="flex flex-col gap-1">
          {navLinks.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm text-fg-secondary transition-colors hover:bg-surface-raised hover:text-fg"
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
