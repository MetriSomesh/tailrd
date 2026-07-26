"use client";

import { ScoreGauge } from "@/components/ui/score-gauge";
import { cn } from "@/lib/cn";
import { Check, X } from "lucide-react";

/**
 * The hero's visual anchor: a faithful mock of the real result panel, styled
 * as a technical spec sheet — framed, ruled, monospace metadata.
 *
 * Showing the actual artefact the product returns is more persuasive than any
 * abstract illustration, and sets an accurate expectation of the output.
 */

const subScores = [
  { label: "Keywords", value: 56 },
  { label: "Skills", value: 100 },
  { label: "Terms", value: 100 },
  { label: "Experience", value: 100 },
];

const covered = ["LLM agents", "Retrieval", "Backend APIs", "Evals"];
const missing = ["Kubernetes"];

export function ScorePreview({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "relative rounded-md border border-border-strong bg-surface-raised hard-shadow",
        className,
      )}
      aria-hidden="true"
    >
      {/* Header — filename + status, a real window bar */}
      <div className="flex items-center gap-2.5 border-b border-border-strong px-4 py-3">
        <span className="flex gap-1">
          <span className="size-2 rounded-full bg-danger" />
          <span className="size-2 rounded-full bg-warning" />
          <span className="size-2 rounded-full bg-success" />
        </span>
        <span className="ml-1 truncate font-mono text-2xs text-fg-tertiary">
          Somesh_Metri_Resume.docx
        </span>
        <span className="ml-auto flex items-center gap-1.5 border border-success/40 bg-success-subtle px-2 py-0.5 font-mono text-2xs uppercase tracking-wide text-success">
          <span className="size-1.5 rounded-full bg-success" />
          Ready
        </span>
      </div>

      <div className="flex flex-col gap-6 p-5 sm:flex-row sm:items-center sm:gap-7 sm:p-6">
        <ScoreGauge score={84.5} size="md" label="ATS SCORE" />

        {/* Sub-scores as ruled key/value rows */}
        <div className="w-full flex-1 divide-y divide-border-subtle border-y border-border-subtle">
          {subScores.map((s) => (
            <div key={s.label} className="flex items-center gap-3 py-2.5">
              <span className="mono-label w-24 shrink-0">{s.label}</span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-[1px] bg-surface-sunken">
                <div className="h-full bg-accent" style={{ width: `${s.value}%` }} />
              </div>
              <span className="w-10 shrink-0 text-right font-mono text-2xs tabular-nums text-fg-secondary">
                {s.value}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Gap tags — the actionable part */}
      <div className="flex flex-wrap items-center gap-1.5 border-t border-border-strong px-5 py-4 sm:px-6">
        {covered.map((c) => (
          <span
            key={c}
            className="inline-flex items-center gap-1 rounded-[2px] border border-success/30 bg-success-subtle px-2 py-0.5 font-mono text-2xs text-success"
          >
            <Check className="size-2.5" />
            {c}
          </span>
        ))}
        {missing.map((m) => (
          <span
            key={m}
            className="inline-flex items-center gap-1 rounded-[2px] border border-danger/30 bg-danger-subtle px-2 py-0.5 font-mono text-2xs text-danger"
          >
            <X className="size-2.5" />
            {m}
          </span>
        ))}
      </div>
    </div>
  );
}
