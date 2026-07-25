import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Refund & Cancellation Policy" };

export default function RefundPolicyPage() {
  return (
    <article className="prose-custom mx-auto max-w-3xl px-6 py-16">
      <h1>Refund &amp; Cancellation Policy</h1>
      <p className="text-fg-secondary">Last updated: July 2026</p>

      <h2>Per-Resume Credits (₹29)</h2>
      <ul>
        <li>Credits are non-refundable once purchased</li>
        <li>If a tailoring job fails due to a system error, the credit is automatically refunded to your balance</li>
        <li>Credits never expire</li>
      </ul>

      <h2>Weekly Subscription (₹149)</h2>
      <ul>
        <li>Cancel anytime — access continues until the end of the current 7-day period</li>
        <li>No prorated refunds for partial periods</li>
        <li>Cancellation takes effect at the next renewal date</li>
      </ul>

      <h2>Monthly Subscription (₹349)</h2>
      <ul>
        <li>Cancel anytime — access continues until the end of the current 30-day period</li>
        <li>No prorated refunds for partial periods</li>
        <li>Cancellation takes effect at the next renewal date</li>
      </ul>

      <h2>System Failures</h2>
      <p>
        If a tailoring job fails due to a system error (not a user input error), any consumed
        entitlement (free-tier count or credit) is automatically refunded. No action needed on your part.
      </p>

      <h2>How to Cancel</h2>
      <p>
        Go to <strong>Billing → Cancel subscription</strong> in the app. Cancellation is
        immediate and requires no support interaction.
      </p>

      <h2>Contact</h2>
      <p>
        For billing disputes or refund requests not covered above, email{" "}
        <a href={`mailto:${SITE.supportEmail}`}>{SITE.supportEmail}</a>.
      </p>
    </article>
  );
}
