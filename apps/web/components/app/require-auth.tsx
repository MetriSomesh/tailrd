"use client";

import { ApiRequestError, getMe, type User } from "@/lib/api";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";

interface AuthState {
  user: User;
}

const AuthContext = createContext<AuthState | null>(null);

/** Access the signed-in user. Only valid inside RequireAuth. */
export function useUser(): User {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useUser must be used within RequireAuth");
  return ctx.user;
}

type Status = "loading" | "authed" | "error";

/**
 * Client-side auth gate for the app section.
 *
 * Calls GET /auth/me on mount. On 401 it redirects to /login (preserving the
 * intended path). While the check is in flight it shows a lightweight loader,
 * so protected content never flashes before auth resolves.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((u) => {
        if (!cancelled) {
          setUser(u);
          setStatus("authed");
        }
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiRequestError && err.problem.status === 401) {
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        } else {
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [router, pathname]);

  if (status === "authed" && user) {
    return <AuthContext.Provider value={{ user }}>{children}</AuthContext.Provider>;
  }

  if (status === "error") {
    return (
      <div className="grid min-h-[60vh] place-items-center px-6 text-center">
        <div className="max-w-sm">
          <h1 className="type-display text-2xl text-fg">Couldn&apos;t reach the server</h1>
          <p className="mt-3 text-sm text-fg-tertiary">
            We couldn&apos;t load your account. Check your connection and try again.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-6 inline-flex h-10 items-center rounded-md border border-border-strong bg-surface-raised px-4 text-sm font-semibold text-fg transition-colors hover:bg-surface-sunken"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Loading
  return (
    <div className="grid min-h-[60vh] place-items-center" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading your account…</span>
      <span
        aria-hidden="true"
        className="size-6 animate-spin rounded-full border-2 border-border-default border-t-accent"
      />
    </div>
  );
}
