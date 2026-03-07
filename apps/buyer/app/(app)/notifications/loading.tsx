export default function NotificationsLoading() {
  return (
    <div className="mx-auto max-w-3xl" aria-busy="true" aria-label="Loading notifications">
      {/* Title skeleton */}
      <div className="relative mb-6 h-8 w-48 overflow-hidden rounded-lg bg-card border border-border">
        <div className="absolute inset-0 animate-shimmer" />
      </div>
      {/* Counter skeleton */}
      <div className="relative mb-3 h-4 w-24 overflow-hidden rounded bg-card border border-border">
        <div className="absolute inset-0 animate-shimmer" />
      </div>
      {/* Item skeletons */}
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="relative overflow-hidden rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2">
              <div className="relative h-5 w-20 overflow-hidden rounded bg-secondary">
                <div className="absolute inset-0 animate-shimmer" />
              </div>
              <div className="relative h-4 w-52 overflow-hidden rounded bg-secondary">
                <div className="absolute inset-0 animate-shimmer" />
              </div>
            </div>
            <div className="relative mt-2 h-3 w-72 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative mt-1 h-3 w-28 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
