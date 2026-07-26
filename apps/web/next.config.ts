import path from "node:path";
import type { NextConfig } from "next";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // The repo is a workspace root with its own lockfile; point tracing at the
  // app directory so Next stops guessing (and warning) about the root.
  outputFileTracingRoot: path.join(__dirname),

  reactStrictMode: true,
  poweredByHeader: false,

  // Hide the floating dev-mode indicator ("N" badge) so it doesn't overlap UI.
  devIndicators: false,

  // Fail the build on type or lint errors rather than shipping broken code.
  typescript: { ignoreBuildErrors: false },
  eslint: { ignoreDuringBuilds: false },

  experimental: {
    // Trim client bundles for icon/util packages added in later phases.
    optimizePackageImports: ["lucide-react"],
    // Rewrite proxying (/api/backend/*) defaults to a 30s upstream timeout.
    // The resume-parse call runs a real LLM (~35s on the opencode backend), so
    // raise it well past that; the backend still caps the work itself.
    proxyTimeout: 120_000,
  },

  async headers() {
    const isProd = process.env.NODE_ENV === "production";
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "geolocation=(), microphone=(), camera=()",
          },
          ...(isProd
            ? [
                {
                  key: "Strict-Transport-Security",
                  value: "max-age=63072000; includeSubDomains; preload",
                },
              ]
            : []),
        ],
      },
    ];
  },

  async rewrites() {
    // Same-origin proxy to the API so auth cookies stay first-party and we
    // avoid third-party cookie restrictions in browsers.
    return [
      {
        source: "/api/backend/:path*",
        destination: `${API_BASE_URL}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
