"use client";

import { cn } from "@/lib/cn";
import { type ReactNode, useEffect, useRef, useState } from "react";

interface RevealProps {
  children: ReactNode;
  /** Delay in ms before this element animates in. Use for stagger. */
  delay?: number;
  className?: string;
  as?: "div" | "section" | "li" | "article" | "ul";
}

/**
 * Scroll-triggered reveal.
 *
 * Progressive enhancement, deliberately:
 * - The hidden state lives in CSS under `html.js`, which the pre-paint theme
 *   script sets. With JS disabled the content renders normally instead of
 *   being stuck at opacity 0.
 * - IntersectionObserver + a CSS transition, so the animation runs on the
 *   compositor and costs no bundle weight.
 * - prefers-reduced-motion reveals immediately with no transform.
 */
export function Reveal({ children, delay = 0, className, as: Tag = "div" }: RevealProps) {
  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(true);
      return;
    }

    // Already in view on mount (above the fold): reveal without waiting.
    const rect = node.getBoundingClientRect();
    if (rect.top < window.innerHeight) {
      setShown(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.05 },
    );
    observer.observe(node);

    // Safety net: never leave content hidden, whatever happens.
    const failsafe = window.setTimeout(() => setShown(true), 2500);

    return () => {
      observer.disconnect();
      window.clearTimeout(failsafe);
    };
  }, []);

  return (
    <Tag
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ref={ref as any}
      data-reveal={shown ? "in" : "out"}
      className={cn("reveal", className)}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </Tag>
  );
}
