"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useState } from "react";
import { Send } from "lucide-react";

/**
 * Tailor page — where users submit a JD to get their resume tailored.
 *
 * Simple form: paste JD text + optional company/role → submit.
 * Shows loading state while the job processes.
 */
export default function TailorPage() {
  const [jdText, setJdText] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const canSubmit = jdText.trim().length >= 50 && !loading;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    // TODO: wire to POST /api/backend/tailor
    await new Promise((r) => setTimeout(r, 1500));
    setSubmitted(true);
    setLoading(false);
  }

  if (submitted) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="rounded-full bg-success-subtle p-4">
          <Send className="h-6 w-6 text-success" />
        </div>
        <h2 className="mt-6 text-xl font-medium text-fg">Job submitted</h2>
        <p className="mt-2 max-w-sm text-sm text-fg-secondary">
          Your resume is being tailored. Check the{" "}
          <a href="/runs" className="text-accent underline underline-offset-2">runs page</a>{" "}
          for progress.
        </p>
        <Button variant="secondary" className="mt-8" onClick={() => setSubmitted(false)}>
          Tailor another
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-medium text-fg">Tailor a resume</h1>
        <p className="mt-1 text-sm text-fg-tertiary">
          Paste a job description and we will rewrite your resume to match it.
        </p>
      </div>

      <Card>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* JD textarea */}
            <div className="space-y-1.5">
              <label htmlFor="jd" className="text-sm font-medium text-fg">
                Job description <span className="text-danger">*</span>
              </label>
              <textarea
                id="jd"
                rows={12}
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste the full job description here (at least 50 characters)..."
                className="w-full resize-y rounded-lg border border-border-default bg-surface-sunken px-4 py-3 text-sm text-fg placeholder:text-fg-quaternary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-colors"
                required
                minLength={50}
              />
              <p className="text-xs text-fg-quaternary">
                {jdText.length < 50
                  ? `${50 - jdText.length} more characters needed`
                  : `${jdText.length} characters`}
              </p>
            </div>

            {/* Company + Role row */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label htmlFor="company" className="text-sm font-medium text-fg">Company</label>
                <input
                  id="company"
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="e.g. Lexi"
                  className="w-full rounded-lg border border-border-default bg-surface-sunken px-4 py-2.5 text-sm text-fg placeholder:text-fg-quaternary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-colors"
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="role" className="text-sm font-medium text-fg">Role</label>
                <input
                  id="role"
                  type="text"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g. AI Engineer"
                  className="w-full rounded-lg border border-border-default bg-surface-sunken px-4 py-2.5 text-sm text-fg placeholder:text-fg-quaternary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-colors"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" loading={loading} disabled={!canSubmit}>
                <Send className="h-4 w-4" />
                Tailor resume
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
