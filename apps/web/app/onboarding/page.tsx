import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Get started",
  robots: { index: false, follow: false },
};

export default function OnboardingPage() {
  return <OnboardingWizard />;
}
