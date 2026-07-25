"use client";

import { ScoreGauge } from "@/components/ui/score-gauge";
import { cn } from "@/lib/cn";
import { Check, FileText, X } from "lucide-react";

/**
 * The hero's visual anchor: a faithful mock of the real result panel.
 *
 * Deliberately not an abstract illustration. Showing the actual artefact the
 * product returns is more persuasive than any graphic, and it sets an accurate
 * expectation of what the user gets.
 */

const subScores = [
  { label: "Keywords", value: 56 },
  { label: "Skills", value: 100 },
  { label: "Terms", value: 100 },
  { label: "Experience", value: 100 },
];

const covered = ["LLM agents", "Retrieval systems", "Backend APIs", "Evals & guardrails"];
const missing = ["Kubernetes"];

export function ScorePreview({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "hairline-top relative rounded-2xl bg-surface-raised p-5 sm:p-6",
        "ring-1 ring-border-subtle shadow-xl",
        className,
      )}
      aria-hidden="true"
    >
      {/* Window chrome — grounds it as a real interface, not a decorative card */}
      <div className="mb-5 flex items-center gap-2.5 border-b border-border-subtle pb-4">
        <FileText className="size-4 text-fg-tertiary" />
        <span className="font-mono text-2xs text-fg-tertiary">Somesh_Metri_Resume.docx</span>
        <span className="ml-auto rounded-full bg-success-subtle px-2 py-0.5 text-2xs font-medium text-success">
          Ready
        </span>
      </div>

      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:gap-7">
        <ScoreGauge score={84.5} size="md" label="ATS score" />

        {/* Sub-scores as small multiples */}
        <div className="grid w-full flex-1 grid-cols-2 gap-x-5 gap-y-3.5">
          {subScores.map((s) => (
            <div key={s.label} className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-2xs text-fg-tertiary">{s.label}</span>
                <span className="font-mono text-2xs tabular-nums text-fg-secondary">
                  {s.value}%
                </span>
              </div>
              <div className="h-1 overflow-hidden rounded-full bg-border-subtle">
                <div className="h-full rounded-full bg-accent" style={{ width: `${s.value}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Gap chips — the actionable part */}
      <div className="mt-6 space-y-2.5 border-t border-border-subtle pt-5">
        <div className="flex flex-wrap items-center gap-1.5">
          {covered.map((c) => (
            <span
              key={c}
              className="inline-flex items-center gap-1 rounded-full bg-success-subtle px-2 py-0.5 text-2xs text-success"
            >
              <Check className="size-2.5" />
              {c}
            </span>
          ))}
          {missing.map((m) => (
            <span
              key={m}
              className="inline-flex items-center gap-1 rounded-full bg-danger-subtle px-2 py-0.5 text-2xs text-danger"
            >
              <X className="size-2.5" />
              {m}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
