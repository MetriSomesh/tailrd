import { cn } from "@/lib/cn";
import Link from "next/link";
import { type AnchorHTMLAttributes, type ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const base =
  "group/btn inline-flex shrink-0 items-center justify-center whitespace-nowrap font-semibold " +
  "transition-[background-color,box-shadow,transform,color,border-color] duration-fast " +
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring " +
  "active:translate-y-px disabled:pointer-events-none disabled:opacity-50";

const variantStyles: Record<Variant, string> = {
  // Chartreuse fill, ink text. Flat and confident — no glow, no gradient.
  primary:
    "bg-accent text-accent-contrast border border-transparent " +
    "hover:bg-accent-hover active:bg-accent-active",
  // Framed. The border does the work, in the strong ink/paper rule colour.
  secondary:
    "bg-surface-raised text-fg border border-border-strong " +
    "hover:bg-surface-sunken",
  ghost: "text-fg-secondary border border-transparent hover:bg-surface-raised hover:text-fg",
  danger:
    "bg-surface-raised text-danger border border-danger/40 hover:bg-danger-subtle",
};

const sizeStyles: Record<Size, string> = {
  sm: "h-8 gap-1.5 rounded-md px-3 text-xs",
  md: "h-10 gap-2 rounded-md px-4 text-sm",
  lg: "h-12 gap-2.5 rounded-md px-6 text-base",
};

function styles(variant: Variant, size: Size, className?: string) {
  return cn(base, variantStyles[variant], sizeStyles[size], className);
}

// ---------------------------------------------------------------------------
// Button
// ---------------------------------------------------------------------------

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(styles(variant, size, className), loading && "pointer-events-none opacity-70")}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </button>
  ),
);
Button.displayName = "Button";

// ---------------------------------------------------------------------------
// ButtonLink — same visuals, renders an <a>.
//
// Wrapping <Button> in an <a> produced broken layout (inline anchor around a
// flex button). This renders the anchor itself, so sizing and alignment hold.
// ---------------------------------------------------------------------------

interface ButtonLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  href: string;
  variant?: Variant;
  size?: Size;
}

export const ButtonLink = forwardRef<HTMLAnchorElement, ButtonLinkProps>(
  ({ className, href, variant = "primary", size = "md", children, ...props }, ref) => {
    const isInternal = href.startsWith("/");
    const cls = styles(variant, size, className);

    if (isInternal) {
      return (
        <Link ref={ref} href={href} className={cls} {...props}>
          {children}
        </Link>
      );
    }
    return (
      <a ref={ref} href={href} className={cls} {...props}>
        {children}
      </a>
    );
  },
);
ButtonLink.displayName = "ButtonLink";

// ---------------------------------------------------------------------------

function Spinner() {
  return (
    <svg className="size-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}
