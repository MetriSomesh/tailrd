import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms of Service" };

export default function TermsPage() {
  return (
    <article className="prose-custom mx-auto max-w-3xl px-6 py-16">
      <h1>Terms of Service</h1>
      <p className="text-fg-secondary">Last updated: July 2026</p>

      <h2>1. Service Description</h2>
      <p>
        {SITE.name} is an AI-powered resume tailoring service that rewrites your resume to
        match a specific job description, scores it against ATS criteria, and generates a
        downloadable DOCX file.
      </p>

      <h2>2. Eligibility</h2>
      <p>You must be at least 18 years old to use this service.</p>

      <h2>3. Account Responsibilities</h2>
      <p>
        You are responsible for maintaining the security of your account credentials and for
        all activity under your account. Notify us immediately if you suspect unauthorized access.
      </p>

      <h2>4. Acceptable Use</h2>
      <p>You agree not to:</p>
      <ul>
        <li>Use the service to generate misleading or fraudulent credentials</li>
        <li>Attempt to circumvent usage limits or fair-use caps</li>
        <li>Upload malicious files or content</li>
        <li>Resell or redistribute generated content as a competing service</li>
      </ul>

      <h2>5. AI-Generated Content</h2>
      <p>
        The service uses AI to rewrite resume content. You are responsible for reviewing and
        verifying all generated content before submitting it to employers. We do not guarantee
        the accuracy of any claims or metrics in generated resumes.
      </p>

      <h2>6. Payment &amp; Refunds</h2>
      <p>
        Payments are processed via Razorpay. See our <a href="/refund-policy">Refund Policy</a> for
        details on cancellations and refunds.
      </p>

      <h2>7. Data &amp; Privacy</h2>
      <p>
        Your data is handled according to our <a href="/privacy">Privacy Policy</a> and in
        compliance with India&apos;s Digital Personal Data Protection Act, 2023.
      </p>

      <h2>8. Service Availability</h2>
      <p>
        We aim for high availability but do not guarantee uninterrupted service. Scheduled
        maintenance will be communicated in advance when possible.
      </p>

      <h2>9. Limitation of Liability</h2>
      <p>
        {SITE.name} is provided &ldquo;as is&rdquo; without warranty. We are not liable for
        outcomes of job applications made using generated resumes.
      </p>

      <h2>10. Contact</h2>
      <p>
        Questions about these terms? Email <a href={`mailto:${SITE.supportEmail}`}>{SITE.supportEmail}</a>.
      </p>
    </article>
  );
}
