"use client";

import { THEME_STORAGE_KEY } from "@/components/theme/theme-script";
import { cn } from "@/lib/cn";
import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

type Choice = "light" | "dark" | "system";

const options: { value: Choice; label: string; Icon: typeof Sun }[] = [
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
  { value: "system", label: "System", Icon: Monitor },
];

function resolve(choice: Choice): "light" | "dark" {
  if (choice === "system") {
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  return choice;
}

/**
 * Segmented light / dark / system control.
 *
 * A segmented control rather than a single toggle: users can tell at a glance
 * whether they are pinned to a theme or following the OS, which a two-state
 * icon button cannot express.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const [choice, setChoice] = useState<Choice>("system");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    setChoice(stored === "light" || stored === "dark" ? stored : "system");
    setMounted(true);
  }, []);

  // Follow the OS live while on "system".
  useEffect(() => {
    if (!mounted || choice !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const apply = () => document.documentElement.setAttribute("data-theme", resolve("system"));
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [choice, mounted]);

  function select(next: Choice) {
    setChoice(next);
    if (next === "system") {
      localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    }
    document.documentElement.setAttribute("data-theme", resolve(next));
  }

  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      className={cn(
        "inline-flex items-center gap-0.5 rounded-full bg-surface-raised p-0.5",
        "ring-1 ring-inset ring-border-subtle",
        className,
      )}
    >
      {options.map(({ value, label, Icon }) => {
        const active = mounted && choice === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={label}
            onClick={() => select(value)}
            className={cn(
              "grid size-7 place-items-center rounded-full transition-colors duration-fast",
              "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring",
              active
                ? "bg-accent text-accent-contrast"
                : "text-fg-tertiary hover:bg-surface-overlay hover:text-fg",
            )}
          >
            <Icon className="size-3.5" aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}
