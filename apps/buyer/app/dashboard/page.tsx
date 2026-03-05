import { Header } from "@/components/Header";
import { DashboardContent } from "@/components/dashboard/DashboardContent";

export default function DashboardPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-6">
        <DashboardContent />
      </main>
    </>
  );
}
