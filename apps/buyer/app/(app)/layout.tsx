import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { OrgProvider } from "@/components/providers/OrgProvider";
import { OnboardingGuard } from "@/components/onboarding/OnboardingGuard";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <OnboardingGuard>
      <OrgProvider>
        <div className="flex h-screen">
          <Sidebar />
          <div className="flex flex-1 flex-col overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-y-auto p-6">{children}</main>
          </div>
          <CommandPalette />
        </div>
      </OrgProvider>
    </OnboardingGuard>
  );
}
