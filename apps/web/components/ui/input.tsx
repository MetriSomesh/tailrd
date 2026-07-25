import { cn } from "@/lib/cn";
import { type InputHTMLAttributes, forwardRef, useId } from "react";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: string;
}

/**
 * Labelled input. Label sits above the field (never placeholder-as-label),
 * error below. Placeholder colour is driven by a token verified for contrast.
 */
export const Field = forwardRef<HTMLInputElement, FieldProps>(
  ({ label, hint, error, className, id, ...props }, ref) => {
    const generated = useId();
    const inputId = id ?? generated;
    const describedBy = error
      ? `${inputId}-error`
      : hint
        ? `${inputId}-hint`
        : undefined;

    return (
      <div className="space-y-1.5">
        <label htmlFor={inputId} className="block text-sm font-medium text-fg">
          {label}
        </label>
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            "w-full rounded-xl border bg-surface-sunken px-3.5 py-2.5 text-sm text-fg",
            "transition-colors placeholder:text-fg-tertiary",
            "focus:outline-none focus:ring-4",
            error
              ? "border-danger focus:border-danger focus:ring-danger/12"
              : "border-border-default focus:border-accent focus:ring-accent/12",
            className,
          )}
          {...props}
        />
        {hint && !error && (
          <p id={`${inputId}-hint`} className="text-2xs text-fg-quaternary">
            {hint}
          </p>
        )}
        {error && (
          <p id={`${inputId}-error`} className="text-2xs text-danger">
            {error}
          </p>
        )}
      </div>
    );
  },
);
Field.displayName = "Field";
