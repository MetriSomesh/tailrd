"use client";

import { useEffect } from "react";

// Replaces the root layout when it (or something above the route) throws, so it
// renders its own <html>/<body> and uses inline styles (the app CSS isn't
// guaranteed to be loaded here).
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          background: "#1b1c22",
          color: "#f5f4f2",
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "24px",
          margin: 0,
        }}
      >
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: "0 0 8px" }}>
          Something went wrong
        </h1>
        <p style={{ fontSize: "0.875rem", color: "#a8a6a1", maxWidth: "28rem", margin: 0 }}>
          The app hit an unexpected error. Please try again.
        </p>
        {error.digest && (
          <p style={{ fontFamily: "monospace", fontSize: "0.7rem", color: "#7c7a75", marginTop: "12px" }}>
            Reference: {error.digest}
          </p>
        )}
        <button
          onClick={reset}
          style={{
            marginTop: "24px",
            background: "#b5690d",
            color: "#fff",
            border: "none",
            padding: "10px 20px",
            borderRadius: "6px",
            fontSize: "0.875rem",
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
