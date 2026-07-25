"use client";

import { GoogleButton } from "@/components/auth/google-button";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { ApiRequestError, api } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api("/auth/login", { json: { email, password } });
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.problem.detail
          : "Could not sign in. Try again.",
      );
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="type-display text-3xl text-fg">Welcome back</h1>
      <p className="mt-2 text-sm text-fg-tertiary">Sign in to keep tailoring.</p>

      <div className="mt-8">
        <GoogleButton label="Sign in with Google" />
      </div>

      <div className="my-6 flex items-center gap-3">
        <span className="h-px flex-1 bg-border-subtle" />
        <span className="text-2xs uppercase tracking-widest text-fg-quaternary">or</span>
        <span className="h-px flex-1 bg-border-subtle" />
      </div>

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-medium text-fg" id="pw-label">
              Password
            </span>
            <Link
              href="/forgot-password"
              className="text-2xs text-accent hover:underline"
            >
              Forgot password?
            </Link>
          </div>
          <input
            aria-labelledby="pw-label"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            className="w-full rounded-xl border border-border-default bg-surface-sunken px-3.5 py-2.5 text-sm text-fg transition-colors placeholder:text-fg-tertiary focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/12"
          />
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-xl bg-danger-subtle px-3.5 py-2.5 text-sm text-danger"
          >
            {error}
          </div>
        )}

        <Button type="submit" size="lg" loading={loading} className="w-full">
          Sign in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-fg-tertiary">
        New here?{" "}
        <Link href="/signup" className="font-medium text-accent hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
