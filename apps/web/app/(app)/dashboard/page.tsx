import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScoreGauge } from "@/components/ui/score-gauge";
import { FileText, Zap, TrendingUp, Plus } from "lucide-react";

/**
 * Dashboard — the first thing a logged-in user sees.
 *
 * Shows: usage summary, latest run score, quick-tailor CTA, recent runs.
 * Data is currently static/mock — wired to the API in Phase 7 polish.
 */
export default function DashboardPage() {
  // Mock data for UI development. Replaced with real API calls.
  const usage = { free_used: 1, free_limit: 3, credit_balance: 0, has_subscription: false };
  const latestScore = 73.6;
  const recentRuns = [
    { id: "1", company: "Lexi", role: "AI Engineer", score: 73.6, status: "succeeded", date: "Jul 25, 2026" },
    { id: "2", company: "Stripe", role: "Backend Engineer", score: null, status: "queued", date: "Jul 25, 2026" },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-medium text-fg">Dashboard</h1>
          <p className="mt-1 text-sm text-fg-tertiary">Your resume tailoring at a glance.</p>
        </div>
        <Button size="md">
          <Plus className="h-4 w-4" />
          Tailor resume
        </Button>
      </div>

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Usage</CardTitle>
            <FileText className="h-4 w-4 text-fg-tertiary" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tabular-nums text-fg">
              {usage.free_used}/{usage.free_limit}
            </p>
            <p className="mt-0.5 text-xs text-fg-quaternary">free resumes this month</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Credits</CardTitle>
            <Zap className="h-4 w-4 text-fg-tertiary" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tabular-nums text-fg">{usage.credit_balance}</p>
            <p className="mt-0.5 text-xs text-fg-quaternary">available credits</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Best Score</CardTitle>
            <TrendingUp className="h-4 w-4 text-fg-tertiary" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tabular-nums text-fg">{latestScore}%</p>
            <p className="mt-0.5 text-xs text-fg-quaternary">latest ATS match</p>
          </CardContent>
        </Card>
      </div>

      {/* Score gauge + recent runs */}
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Score */}
        <Card className="flex flex-col items-center justify-center py-8">
          <div className="relative">
            <ScoreGauge score={latestScore} size="lg" />
          </div>
          <p className="mt-4 text-xs text-fg-quaternary">Latest run score</p>
        </Card>

        {/* Recent runs */}
        <Card>
          <CardHeader>
            <CardTitle>Recent runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentRuns.map((run) => (
                <div key={run.id} className="flex items-center justify-between rounded-lg border border-border-subtle px-4 py-3">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-fg">{run.company} — {run.role}</span>
                    <span className="text-xs text-fg-quaternary">{run.date}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {run.score !== null ? (
                      <span className="rounded-full bg-success-subtle px-2.5 py-0.5 text-xs font-medium tabular-nums text-success">
                        {run.score}%
                      </span>
                    ) : (
                      <span className="rounded-full bg-accent-subtle px-2.5 py-0.5 text-xs font-medium text-accent">
                        {run.status}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
