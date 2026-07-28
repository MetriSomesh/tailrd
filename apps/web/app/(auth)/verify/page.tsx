"use client";

import { Button, ButtonLink } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { ApiRequestError, api } from "@/lib/api";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

type Phase = "verifying" | "success" | "error" | "no-token";

function VerifyInner() {
  const token = useSearchParams().get("token");
  const [phase, setPhase] = useState<Phase>(token ? "verifying" : "no-token");
  const [detail, setDetail] = useState<string>("");
  const ran = useRef(false);

  useEffect(() => {
    if (!token || ran.current) return;
    ran.current = true; // guard against React strict-mode double-invoke
    (async () => {
      try {
        await api("/auth/verify-email", { json: { token } });
        setPhase("success");
      } catch (err) {
        setDetail(
          err instanceof ApiRequestError
            ? err.problem.detail
            : "We couldn't verify your email. The link may have expired.",
        );
        setPhase("error");
      }
    })();
  }, [token]);

  if (phase === "verifying") {
    return (
      <div className="text-center">
        <div className="mx-auto grid size-12 place-items-center rounded-md border border-border-default">
          <Loader2 className="size-5 animate-spin text-fg-tertiary" />
        </div>
        <h1 className="type-display mt-5 text-2xl text-fg">Verifying your email</h1>
        <p className="mt-2 text-sm text-fg-tertiary">One moment…</p>
      </div>
    );
  }

  if (phase === "success") {
    return (
      <div className="text-center">
        <div className="mx-auto grid size-12 place-items-center rounded-md border border-success/40 bg-success-subtle">
          <CheckCircle2 className="size-5 text-success" />
        </div>
        <h1 className="type-display mt-5 text-2xl text-fg">Email verified</h1>
        <p className="mt-2 text-sm text-fg-tertiary">
          Your account is ready. You can now tailor resumes.
        </p>
        <ButtonLink href="/dashboard" size="lg" className="mt-6 w-full">
          Go to dashboard
        </ButtonLink>
      </div>
    );
  }

  // error / no-token — offer to resend a fresh link.
  return (
    <div>
      <div className="text-center">
        <div className="mx-auto grid size-12 place-items-center rounded-md border border-danger/40 bg-danger-subtle">
          <AlertCircle className="size-5 text-danger" />
        </div>
        <h1 className="type-display mt-5 text-2xl text-fg">
          {phase === "no-token" ? "Invalid link" : "Verification failed"}
        </h1>
        <p className="mt-2 text-sm text-fg-tertiary">
          {phase === "no-token"
            ? "This verification link is missing its token. Request a new one below."
            : detail}
        </p>
      </div>
      <ResendVerification />
      <p className="mt-6 text-center text-sm text-fg-tertiary">
        <Link href="/login" className="font-medium text-accent-text hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}

function ResendVerification() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api("/auth/resend-verification", { json: { email } });
    } catch {
      // Always show the same confirmation (don't leak account existence).
    }
    setSent(true);
    setLoading(false);
  }

  if (sent) {
    return (
      <p className="mt-6 rounded-md border border-border-default bg-surface-sunken px-4 py-3 text-center text-sm text-fg-secondary">
        If {email || "that address"} is registered and unverified, a new link is on its way.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
      <Field
        label="Resend verification to"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
      />
      <Button type="submit" size="lg" loading={loading} className="w-full">
        Send a new link
      </Button>
    </form>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyInner />
    </Suspense>
  );
}
