export default function NotificationsLoading() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-6">
      <div className="mb-4 h-7 w-40 animate-pulse rounded bg-gray-200" />
      <div className="mb-4 h-4 w-20 animate-pulse rounded bg-gray-100" />

      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-lg border border-gray-200 bg-white p-4"
          >
            <div className="flex items-center gap-2">
              <div className="h-5 w-16 animate-pulse rounded bg-gray-200" />
              <div className="h-4 w-48 animate-pulse rounded bg-gray-200" />
            </div>
            <div className="mt-2 h-3 w-64 animate-pulse rounded bg-gray-100" />
            <div className="mt-1 h-3 w-28 animate-pulse rounded bg-gray-100" />
          </div>
        ))}
      </div>
    </main>
  );
}
