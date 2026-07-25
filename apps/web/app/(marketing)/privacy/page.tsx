import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy Policy" };

export default function PrivacyPage() {
  return (
    <article className="prose-custom mx-auto max-w-3xl px-6 py-16">
      <h1>Privacy Policy</h1>
      <p className="text-fg-secondary">Last updated: July 2026</p>

      <h2>1. Data We Collect</h2>
      <ul>
        <li><strong>Account data:</strong> name, email address, hashed password</li>
        <li><strong>Profile data:</strong> resume content (education, experience, skills, projects)</li>
        <li><strong>Usage data:</strong> job descriptions submitted, generated resumes, ATS scores</li>
        <li><strong>Technical data:</strong> hashed IP addresses, user agent, timestamps</li>
        <li><strong>Payment data:</strong> transaction IDs (processed by Razorpay; we never store card numbers)</li>
      </ul>

      <h2>2. How We Use Your Data</h2>
      <ul>
        <li>To provide the resume tailoring service</li>
        <li>To enforce usage quotas and prevent abuse</li>
        <li>To send transactional emails (verification, password reset)</li>
        <li>To improve the service quality and scoring accuracy</li>
      </ul>

      <h2>3. Data Storage &amp; Security</h2>
      <p>
        Data is stored in encrypted databases. Generated DOCX files are stored in AWS S3
        with server-side encryption and auto-deleted after 90 days. IP addresses are stored
        as irreversible hashes.
      </p>

      <h2>4. Your Rights (DPDP Act, 2023)</h2>
      <ul>
        <li><strong>Access:</strong> Export all your data via Settings → Export Data</li>
        <li><strong>Correction:</strong> Edit your profile at any time</li>
        <li><strong>Erasure:</strong> Delete your account via Settings → Delete Account (30-day grace period)</li>
        <li><strong>Portability:</strong> Data export produces a machine-readable JSON file</li>
      </ul>

      <h2>5. Data Retention</h2>
      <ul>
        <li>DOCX files: 90 days</li>
        <li>Run metadata and scores: 12 months</li>
        <li>Account data: until deletion requested</li>
        <li>After account deletion: permanently purged within 30 days</li>
      </ul>

      <h2>6. Third-Party Services</h2>
      <ul>
        <li><strong>Razorpay:</strong> Payment processing (their <a href="https://razorpay.com/privacy/" target="_blank" rel="noopener">privacy policy</a>)</li>
        <li><strong>AWS:</strong> Infrastructure and file storage</li>
        <li><strong>Resend:</strong> Transactional email delivery</li>
      </ul>

      <h2>7. Cookies</h2>
      <p>
        We use essential cookies only: authentication tokens and CSRF protection. No tracking
        cookies, no third-party analytics cookies. PostHog analytics uses first-party data only.
      </p>

      <h2>8. Grievance Officer</h2>
      <p>
        For any privacy concerns or data requests, contact our Grievance Officer at{" "}
        <a href={`mailto:${SITE.supportEmail}`}>{SITE.supportEmail}</a>.
      </p>
    </article>
  );
}
