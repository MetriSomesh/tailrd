"use client";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { ApiRequestError, api } from "@/lib/api";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

function ResetInner() {
  const token = useSearchParams().get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!token) {
      setError("This reset link is missing its token. Request a new one.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }

    setLoading(true);
    try {
      await api("/auth/reset-password", { json: { token, password } });
      setDone(true);
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.problem.detail
          : "Something went wrong. The link may have expired.",
      );
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div className="text-center">
        <div className="mx-auto grid size-12 place-items-center rounded-md border border-success/40 bg-success-subtle">
          <CheckCircle2 className="size-5 text-success" />
        </div>
        <h1 className="type-display mt-5 text-2xl text-fg">Password reset</h1>
        <p className="mt-2 text-sm text-fg-tertiary">
          You can now sign in with your new password.
        </p>
        <Link
          href="/login"
          className="mt-6 inline-block text-sm font-medium text-accent-text hover:underline"
        >
          Go to sign in
        </Link>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="text-center">
        <div className="mx-auto grid size-12 place-items-center rounded-md border border-danger/40 bg-danger-subtle">
          <AlertCircle className="size-5 text-danger" />
        </div>
        <h1 className="type-display mt-5 text-2xl text-fg">Invalid link</h1>
        <p className="mt-2 text-sm text-fg-tertiary">
          This reset link is missing its token or is malformed.
        </p>
        <Link
          href="/forgot-password"
          className="mt-6 inline-block text-sm font-medium text-accent-text hover:underline"
        >
          Request a new link
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="type-display text-3xl text-fg">Set a new password</h1>
      <p className="mt-2 text-sm text-fg-tertiary">Choose a strong password you don't use elsewhere.</p>

      <form onSubmit={onSubmit} className="mt-8 space-y-4" noValidate>
        <Field
          label="New password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 8 characters"
        />
        <Field
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Re-enter your password"
        />

        {error && (
          <div
            role="alert"
            className="rounded-md border border-danger/40 bg-danger-subtle px-4 py-3 text-sm text-danger"
          >
            {error}
          </div>
        )}

        <Button type="submit" size="lg" loading={loading} className="w-full">
          Reset password
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-fg-tertiary">
        Remembered it?{" "}
        <Link href="/login" className="font-medium text-accent-text hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetInner />
    </Suspense>
  );
}
