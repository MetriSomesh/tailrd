import { SITE } from "@/lib/site";

/**
 * JSON-LD structured data for search engine rich results.
 * Rendered as a <script type="application/ld+json"> in the page.
 */

interface JsonLdProps {
  data: Record<string, unknown>;
}

export function JsonLd({ data }: JsonLdProps) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

/** SoftwareApplication schema for the home page. */
export function AppJsonLd() {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        name: SITE.name,
        description: SITE.description,
        url: SITE.url,
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: [
          {
            "@type": "Offer",
            price: "0",
            priceCurrency: "INR",
            description: "Free tier: 3 resumes per month",
          },
          {
            "@type": "Offer",
            price: "29",
            priceCurrency: "INR",
            description: "Per-resume credit",
          },
          {
            "@type": "Offer",
            price: "149",
            priceCurrency: "INR",
            description: "Weekly unlimited plan",
          },
          {
            "@type": "Offer",
            price: "349",
            priceCurrency: "INR",
            description: "Monthly unlimited plan",
          },
        ],
      }}
    />
  );
}

/** FAQ schema for the pricing page. */
export function PricingFaqJsonLd() {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: [
          {
            "@type": "Question",
            name: "How many free resumes do I get?",
            acceptedAnswer: {
              "@type": "Answer",
              text: "You get 3 free tailored resumes per calendar month. No credit card required.",
            },
          },
          {
            "@type": "Question",
            name: "What does 'unlimited' mean?",
            acceptedAnswer: {
              "@type": "Answer",
              text: "Unlimited plans allow up to 15 resumes per day (60/week or 150/month). This fair-use cap prevents abuse while being generous for even the most active job seekers.",
            },
          },
          {
            "@type": "Question",
            name: "Do credits expire?",
            acceptedAnswer: {
              "@type": "Answer",
              text: "No. Credits purchased at ₹29 each never expire and can be used anytime.",
            },
          },
          {
            "@type": "Question",
            name: "What happens if a job fails?",
            acceptedAnswer: {
              "@type": "Answer",
              text: "If a tailoring job fails due to a system error, your entitlement (free count or credit) is automatically refunded. No action needed.",
            },
          },
        ],
      }}
    />
  );
}
