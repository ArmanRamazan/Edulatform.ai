export default function BadgesLoading() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-6">
      <div className="mb-6 h-7 w-40 animate-pulse rounded bg-gray-200" />

      {/* Stats row */}
      <div className="mb-8 grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center"
          >
            <div className="mx-auto mb-2 h-7 w-12 animate-pulse rounded bg-gray-200" />
            <div className="mx-auto h-4 w-20 animate-pulse rounded bg-gray-100" />
          </div>
        ))}
      </div>

      {/* Badge grid */}
      <div className="mb-4 h-5 w-20 animate-pulse rounded bg-gray-200" />
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="flex flex-col items-center rounded-lg border border-gray-200 p-4"
          >
            <div className="h-8 w-8 animate-pulse rounded-full bg-gray-200" />
            <div className="mt-2 h-4 w-20 animate-pulse rounded bg-gray-100" />
            <div className="mt-1 h-3 w-16 animate-pulse rounded bg-gray-100" />
          </div>
        ))}
      </div>
    </main>
  );
}
