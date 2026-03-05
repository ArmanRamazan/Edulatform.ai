export default function ConceptsLoading() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-4 h-4 w-40 animate-pulse rounded bg-gray-200" />
      <div className="mb-6 h-6 w-48 animate-pulse rounded bg-gray-200" />

      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
          >
            <div className="space-y-1">
              <div className="h-4 w-32 animate-pulse rounded bg-gray-200" />
              <div className="h-3 w-48 animate-pulse rounded bg-gray-100" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
