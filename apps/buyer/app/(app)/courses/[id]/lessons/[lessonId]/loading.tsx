export default function LessonLoading() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <div className="mb-4 h-4 w-48 animate-pulse rounded bg-gray-200" />
      <div className="flex gap-6">
        <aside className="hidden w-64 shrink-0 md:block">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <div className="h-3 w-20 animate-pulse rounded bg-gray-200" />
                <div className="h-4 w-full animate-pulse rounded bg-gray-100" />
                <div className="h-4 w-full animate-pulse rounded bg-gray-100" />
              </div>
            ))}
          </div>
        </aside>
        <main className="min-w-0 flex-1">
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <div className="mb-4 h-7 w-1/2 animate-pulse rounded bg-gray-200" />
            <div className="space-y-2">
              <div className="h-4 w-full animate-pulse rounded bg-gray-100" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-gray-100" />
              <div className="h-4 w-3/4 animate-pulse rounded bg-gray-100" />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
