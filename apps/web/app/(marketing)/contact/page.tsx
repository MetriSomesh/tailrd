import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Contact" };

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-xl px-6 py-16">
      <h1 className="text-2xl font-medium text-fg">Contact</h1>
      <p className="mt-3 text-fg-secondary">
        Have a question, found a bug, or need help with your account? We typically respond within 24 hours.
      </p>

      <div className="mt-8 space-y-4">
        <div className="rounded-lg border border-border-subtle p-4">
          <p className="text-sm font-medium text-fg">Email</p>
          <a href={`mailto:${SITE.supportEmail}`} className="text-sm text-accent hover:underline">
            {SITE.supportEmail}
          </a>
        </div>

        <div className="rounded-lg border border-border-subtle p-4">
          <p className="text-sm font-medium text-fg">Response time</p>
          <p className="text-sm text-fg-secondary">Within 24 hours on business days</p>
        </div>

        <div className="rounded-lg border border-border-subtle p-4">
          <p className="text-sm font-medium text-fg">Grievance Officer (DPDP Act)</p>
          <p className="text-sm text-fg-secondary">
            For data privacy concerns, contact the same email above with subject &ldquo;DPDP Request&rdquo;.
          </p>
        </div>
      </div>
    </div>
  );
}
