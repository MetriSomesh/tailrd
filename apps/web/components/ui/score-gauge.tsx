"use client";

import { cn } from "@/lib/cn";
import { useEffect, useRef, useState } from "react";

interface ScoreGaugeProps {
  score: number;
  label?: string;
  size?: "sm" | "md" | "lg";
  animate?: boolean;
  className?: string;
}

const sizes = {
  sm: { box: 84, stroke: 7, value: "text-xl", label: "text-2xs" },
  md: { box: 132, stroke: 9, value: "text-3xl", label: "text-2xs" },
  lg: { box: 184, stroke: 11, value: "text-5xl", label: "text-xs" },
};

function bandColor(score: number): string {
  if (score >= 80) return "var(--success)";
  if (score >= 60) return "var(--accent)";
  if (score >= 40) return "var(--warning)";
  return "var(--danger)";
}

/**
 * Radial ATS score gauge.
 *
 * The one deliberately theatrical moment in the product: the arc draws and the
 * number counts up together over 900ms. Everything else in the UI is 150-220ms.
 */
export function ScoreGauge({
  score,
  label = "ATS score",
  size = "md",
  animate = true,
  className,
}: ScoreGaugeProps) {
  const { box, stroke, value: valueSize, label: labelSize } = sizes[size];
  const radius = (box - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  const [progress, setProgress] = useState(animate ? 0 : score);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(!animate);

  // Only animate once the gauge is actually on screen.
  useEffect(() => {
    if (!animate) return;
    const node = wrapperRef.current;
    if (!node) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setProgress(score);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [animate, score]);

  useEffect(() => {
    if (!inView || !animate) return;
    const duration = 900;
    const start = performance.now();
    let frame = 0;

    function tick(now: number) {
      const t = Math.min((now - start) / duration, 1);
      // ease-out-quart
      setProgress(score * (1 - Math.pow(1 - t, 4)));
      if (t < 1) frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [inView, score, animate]);

  const offset = circumference - (progress / 100) * circumference;
  const colour = bandColor(score);

  return (
    <div
      ref={wrapperRef}
      className={cn("relative grid shrink-0 place-items-center", className)}
      style={{ width: box, height: box }}
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={score}
      aria-label={label}
    >
      {/* Soft halo in the score's own colour — gives the number presence. */}
      <div
        aria-hidden="true"
        className="absolute inset-[18%] rounded-full blur-2xl"
        style={{ background: colour, opacity: 0.14 }}
      />

      <svg
        width={box}
        height={box}
        viewBox={`0 0 ${box} ${box}`}
        className="absolute inset-0 -rotate-90"
        aria-hidden="true"
      >
        <circle
          cx={box / 2}
          cy={box / 2}
          r={radius}
          fill="none"
          stroke="var(--border-subtle)"
          strokeWidth={stroke}
        />
        <circle
          cx={box / 2}
          cy={box / 2}
          r={radius}
          fill="none"
          stroke={colour}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>

      {/* Centred readout. Grid-centred on the wrapper, so it cannot drift. */}
      <div className="relative z-10 flex flex-col items-center leading-none">
        <span
          className={cn("font-mono font-semibold tabular-nums text-fg", valueSize)}
          style={{ letterSpacing: "-0.04em" }}
        >
          {progress.toFixed(progress < 100 && score % 1 !== 0 ? 1 : 0)}
        </span>
        <span className={cn("mt-1 text-fg-tertiary", labelSize)}>{label}</span>
      </div>
    </div>
  );
}
