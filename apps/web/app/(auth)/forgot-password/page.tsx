"use client";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { api } from "@/lib/api";
import { CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    // The API always returns success to avoid leaking whether an email exists.
    try {
      await api("/auth/forgot-password", { json: { email } });
    } catch {
      // Swallow: we show the same confirmation regardless.
    }
    setSent(true);
    setLoading(false);
  }

  if (sent) {
    return (
      <div className="text-center">
        <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-success-subtle ring-1 ring-inset ring-success/20">
          <CheckCircle2 className="size-5 text-success" />
        </div>
        <h1 className="type-display mt-5 text-2xl text-fg">Check your inbox</h1>
        <p className="mt-2 text-sm text-fg-tertiary">
          If an account exists for {email}, a reset link is on its way.
        </p>
        <Link
          href="/login"
          className="mt-6 inline-block text-sm font-medium text-accent hover:underline"
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="type-display text-3xl text-fg">Reset password</h1>
      <p className="mt-2 text-sm text-fg-tertiary">
        Enter your email and we will send a reset link.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-4" noValidate>
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
        <Button type="submit" size="lg" loading={loading} className="w-full">
          Send reset link
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-fg-tertiary">
        Remembered it?{" "}
        <Link href="/login" className="font-medium text-accent hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
