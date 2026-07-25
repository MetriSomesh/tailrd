"use client";

import { GoogleButton } from "@/components/auth/google-button";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { ApiRequestError, api } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api("/auth/signup", { json: { name, email, password } });
      router.push("/onboarding");
    } catch (err) {
      setError(
        err instanceof ApiRequestError ? err.problem.detail : "Something went wrong. Try again.",
      );
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="type-display text-3xl text-fg">Create your account</h1>
      <p className="mt-2 text-sm text-fg-tertiary">
        Three tailored resumes a month, free. No card needed.
      </p>

      <div className="mt-8">
        <GoogleButton label="Sign up with Google" />
      </div>

      <div className="my-6 flex items-center gap-3">
        <span className="h-px flex-1 bg-border-subtle" />
        <span className="text-2xs uppercase tracking-widest text-fg-quaternary">or</span>
        <span className="h-px flex-1 bg-border-subtle" />
      </div>

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field
          label="Name"
          type="text"
          autoComplete="name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Somesh Metri"
        />
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
        <Field
          label="Password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 8 characters"
          hint="Use 8 or more characters with a mix of letters and numbers."
        />

        {error && (
          <div
            role="alert"
            className="rounded-xl bg-danger-subtle px-3.5 py-2.5 text-sm text-danger"
          >
            {error}
          </div>
        )}

        <Button type="submit" size="lg" loading={loading} className="w-full">
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-fg-tertiary">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-accent hover:underline">
          Sign in
        </Link>
      </p>

      <p className="mt-6 text-center text-2xs leading-relaxed text-fg-quaternary">
        By continuing you agree to our{" "}
        <Link href="/terms" className="underline hover:text-fg-tertiary">
          Terms
        </Link>{" "}
        and{" "}
        <Link href="/privacy" className="underline hover:text-fg-tertiary">
          Privacy Policy
        </Link>
        .
      </p>
    </div>
  );
}
