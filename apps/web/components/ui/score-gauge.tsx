"use client";

import { cn } from "@/lib/cn";
import { useEffect, useState } from "react";

interface ScoreGaugeProps {
  score: number; // 0-100
  label?: string;
  size?: "sm" | "md" | "lg";
  animate?: boolean;
  className?: string;
}

const sizes = {
  sm: { box: 80, stroke: 6, text: "text-lg", label: "text-2xs" },
  md: { box: 140, stroke: 8, text: "text-3xl", label: "text-xs" },
  lg: { box: 200, stroke: 10, text: "text-4xl", label: "text-sm" },
};

function scoreColor(score: number): string {
  if (score >= 80) return "var(--success)";
  if (score >= 60) return "var(--accent)";
  if (score >= 40) return "var(--warning)";
  return "var(--danger)";
}

export function ScoreGauge({
  score,
  label = "ATS Score",
  size = "md",
  animate = true,
  className,
}: ScoreGaugeProps) {
  const [displayed, setDisplayed] = useState(animate ? 0 : score);
  const config = sizes[size];
  const radius = (config.box - config.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (displayed / 100) * circumference;
  const offset = circumference - progress;

  useEffect(() => {
    if (!animate) {
      setDisplayed(score);
      return;
    }
    // Count up over 340ms (the "score reveal" moment from DESIGN.md)
    const duration = 340;
    const start = performance.now();
    const from = 0;
    const to = score;

    function tick(now: number) {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1);
      // ease-out-quart
      const eased = 1 - Math.pow(1 - t, 4);
      setDisplayed(Math.round(from + (to - from) * eased));
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }, [score, animate]);

  return (
    <div className={cn("flex flex-col items-center gap-2", className)} role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={score} aria-label={label}>
      <svg
        width={config.box}
        height={config.box}
        viewBox={`0 0 ${config.box} ${config.box}`}
        className="-rotate-90"
      >
        {/* Background track */}
        <circle
          cx={config.box / 2}
          cy={config.box / 2}
          r={radius}
          fill="none"
          stroke="var(--border-subtle)"
          strokeWidth={config.stroke}
        />
        {/* Progress arc */}
        <circle
          cx={config.box / 2}
          cy={config.box / 2}
          r={radius}
          fill="none"
          stroke={scoreColor(score)}
          strokeWidth={config.stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-[stroke-dashoffset] duration-slow"
          style={{ transitionTimingFunction: "var(--ease-out-quart)" }}
        />
      </svg>
      {/* Score number overlaid */}
      <div className="absolute flex flex-col items-center justify-center" style={{ width: config.box, height: config.box }}>
        <span className={cn("font-mono font-semibold tabular-nums", config.text)}>{displayed}</span>
        <span className={cn("text-fg-tertiary", config.label)}>{label}</span>
      </div>
    </div>
  );
}
