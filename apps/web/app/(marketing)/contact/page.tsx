import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Contact" };

export default function ContactPage() {
  return (
    <div className="container-page max-w-2xl py-16 lg:py-20">
      <p className="eyebrow flex items-center gap-2">
        <span className="inline-block h-px w-6 bg-accent" />
        Support
      </p>
      <h1 className="type-display mt-4 text-fluid-h2 text-fg">Contact</h1>
      <p className="mt-4 max-w-md text-fg-secondary">
        Have a question, found a bug, or need help with your account? We typically respond within 24 hours.
      </p>

      <div className="mt-10 overflow-hidden rounded-md border border-border-strong divide-y divide-border-subtle">
        <div className="grid grid-cols-1 gap-1 p-5 sm:grid-cols-[10rem_1fr]">
          <p className="mono-label sm:pt-0.5">Email</p>
          <a
            href={`mailto:${SITE.supportEmail}`}
            className="text-sm font-medium text-accent-text hover:underline"
          >
            {SITE.supportEmail}
          </a>
        </div>

        <div className="grid grid-cols-1 gap-1 p-5 sm:grid-cols-[10rem_1fr]">
          <p className="mono-label sm:pt-0.5">Response time</p>
          <p className="text-sm text-fg-secondary">Within 24 hours on business days</p>
        </div>

        <div className="grid grid-cols-1 gap-1 p-5 sm:grid-cols-[10rem_1fr]">
          <p className="mono-label sm:pt-0.5">Grievance Officer</p>
          <p className="text-sm text-fg-secondary">
            For DPDP Act data privacy concerns, email the address above with subject
            &ldquo;DPDP Request&rdquo;.
          </p>
        </div>
      </div>
    </div>
  );
}
