import { Header } from "@/components/Header";

export default function DashboardLoading() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-6">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="h-7 w-56 animate-pulse rounded-lg bg-gray-200" />
              <div className="mt-2 h-4 w-36 animate-pulse rounded bg-gray-100" />
            </div>
            <div className="h-8 w-24 animate-pulse rounded-full bg-gray-200" />
          </div>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <div className="h-56 animate-pulse rounded-2xl bg-gray-100" />
            <div className="h-56 animate-pulse rounded-2xl bg-gray-100" />
          </div>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <div className="h-44 animate-pulse rounded-2xl bg-gray-100" />
            <div className="h-44 animate-pulse rounded-2xl bg-gray-100" />
          </div>
        </div>
      </main>
    </>
  );
}
