import { Card } from "@/components/ui/card";
import { Download, Clock, CheckCircle, XCircle } from "lucide-react";

/**
 * Runs page — lists all tailoring runs with status, score, and download.
 */

// Mock data. Replaced with API fetch.
const runs = [
  { id: "r1", company: "Lexi", role: "AI Engineer", score: 73.6, status: "succeeded", date: "2026-07-25T16:30:00" },
  { id: "r2", company: "Stripe", role: "Backend Eng", score: 65.2, status: "succeeded", date: "2026-07-24T10:15:00" },
  { id: "r3", company: "Vercel", role: "Full Stack", score: null, status: "failed", date: "2026-07-23T09:00:00" },
  { id: "r4", company: "Razorpay", role: "SDE-2", score: null, status: "queued", date: "2026-07-25T17:00:00" },
];

const statusIcon: Record<string, React.ReactNode> = {
  succeeded: <CheckCircle className="h-4 w-4 text-success" />,
  failed: <XCircle className="h-4 w-4 text-danger" />,
  queued: <Clock className="h-4 w-4 text-accent" />,
  running: <Clock className="h-4 w-4 text-accent animate-pulse" />,
};

export default function RunsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-medium text-fg">Run History</h1>
        <p className="mt-1 text-sm text-fg-tertiary">All your tailored resumes and their scores.</p>
      </div>

      <div className="space-y-3">
        {runs.map((run) => (
          <Card key={run.id} className="flex items-center gap-4 px-5 py-4">
            <div className="flex-shrink-0">
              {statusIcon[run.status]}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium text-fg">
                {run.company} — {run.role}
              </p>
              <p className="text-xs text-fg-quaternary">
                {new Date(run.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {run.score !== null && (
                <span className="rounded-full bg-surface-overlay px-2.5 py-0.5 text-xs font-mono font-medium tabular-nums text-fg-secondary">
                  {run.score}%
                </span>
              )}
              {run.status === "succeeded" && (
                <button
                  className="rounded-md p-1.5 text-fg-tertiary hover:bg-surface-overlay hover:text-fg transition-colors"
                  aria-label={`Download resume for ${run.company}`}
                >
                  <Download className="h-4 w-4" />
                </button>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
