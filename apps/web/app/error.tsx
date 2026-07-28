"use client";

import { Button, ButtonLink } from "@/components/ui/button";
import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface to the browser console (and any client error reporter).
    console.error(error);
  }, [error]);

  return (
    <main
      id="main"
      className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-6 text-center"
    >
      <p className="font-mono text-2xs uppercase tracking-widest text-fg-quaternary">
        Something went wrong
      </p>
      <h1 className="type-display mt-4 text-3xl text-fg">This page hit a snag</h1>
      <p className="mt-3 text-pretty text-sm leading-relaxed text-fg-tertiary">
        An unexpected error occurred. You can try again, or head back and retry from there.
      </p>
      {error.digest && (
        <p className="mt-4 font-mono text-2xs text-fg-quaternary">Reference: {error.digest}</p>
      )}
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Button onClick={reset}>Try again</Button>
        <ButtonLink href="/dashboard" variant="secondary">
          Back to dashboard
        </ButtonLink>
      </div>
    </main>
  );
}
