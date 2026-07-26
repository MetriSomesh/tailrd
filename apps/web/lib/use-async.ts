"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface AsyncState<T> {
  data: T | undefined;
  error: unknown;
  loading: boolean;
}

/**
 * Minimal data-fetching hook for client components.
 *
 * Runs `fn` on mount (and when `deps` change), tracking loading/error/data.
 * Returns a `refetch` for manual refresh after mutations. Deliberately tiny —
 * the app has few data screens, so a full query library would be overkill.
 */
export function useAsync<T>(
  fn: () => Promise<T>,
  deps: unknown[] = [],
): AsyncState<T> & { refetch: () => void } {
  const [state, setState] = useState<AsyncState<T>>({
    data: undefined,
    error: undefined,
    loading: true,
  });

  // Keep the latest fn without making it a dependency.
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const run = useCallback(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: undefined }));
    fnRef.current()
      .then((data) => {
        if (!cancelled) setState({ data, error: undefined, loading: false });
      })
      .catch((error) => {
        if (!cancelled) setState((s) => ({ ...s, error, loading: false }));
      });
    return () => {
      cancelled = true;
    };
  }, deps);

  useEffect(run, [run]);

  const refetch = useCallback(() => {
    run();
  }, [run]);

  return { ...state, refetch };
}
