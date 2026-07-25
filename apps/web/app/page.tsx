import { SITE } from "@/lib/site";

/**
 * Phase 0 placeholder. Exists to verify the token system renders and the
 * build pipeline works. Replaced with the real landing page in Phase 8.
 */
export default function Home() {
  return (
    <main
      id="main"
      className="mx-auto flex min-h-dvh max-w-2xl flex-col justify-center px-6 py-24"
    >
      <p className="eyebrow mb-5">Phase 0 · Scaffold</p>

      <h1 className="display text-5xl text-fg">{SITE.name}</h1>

      <p className="mt-5 max-w-lg text-lg text-fg-secondary">
        {SITE.description}
      </p>

      <div className="mt-10 flex flex-wrap items-center gap-3">
        <span className="rounded-full bg-accent px-4 py-1.5 text-sm font-medium text-accent-contrast">
          Accent
        </span>
        <span className="rounded-full bg-surface-raised px-4 py-1.5 text-sm text-fg-secondary ring-1 ring-border-default ring-inset">
          Raised
        </span>
        <span className="rounded-full bg-success-subtle px-4 py-1.5 text-sm text-success">
          Success
        </span>
        <span className="rounded-full bg-danger-subtle px-4 py-1.5 text-sm text-danger">
          Danger
        </span>
      </div>

      <dl className="mt-14 grid gap-x-8 gap-y-4 border-t border-border-subtle pt-8 text-sm sm:grid-cols-2">
        <div className="flex justify-between gap-4">
          <dt className="text-fg-tertiary">Frontend</dt>
          <dd className="font-mono text-2xs text-fg-secondary">Next.js · Vercel</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-fg-tertiary">Backend</dt>
          <dd className="font-mono text-2xs text-fg-secondary">FastAPI · EC2</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-fg-tertiary">Engine</dt>
          <dd className="font-mono text-2xs text-fg-secondary">Hermes · OpenCode</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-fg-tertiary">Payments</dt>
          <dd className="font-mono text-2xs text-fg-secondary">Razorpay</dd>
        </div>
      </dl>
    </main>
  );
}
