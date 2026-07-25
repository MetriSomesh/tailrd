import { AppHeader } from "@/components/app/app-header";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard",
  robots: { index: false, follow: false },
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader />
      <main id="main" className="container-page flex-1 py-8 lg:py-10">
        {children}
      </main>
    </div>
  );
}
