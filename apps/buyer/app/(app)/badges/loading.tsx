export default function BadgesLoading() {
  return (
    <div className="mx-auto max-w-4xl" aria-busy="true" aria-label="Loading badges">
      {/* Title */}
      <div className="relative mb-6 h-8 w-40 overflow-hidden rounded-lg bg-card border border-border">
        <div className="absolute inset-0 animate-shimmer" />
      </div>

      {/* Stats row */}
      <div className="mb-8 grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="relative overflow-hidden rounded-xl border border-border bg-card p-4 text-center">
            <div className="relative mx-auto mb-2 h-5 w-5 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative mx-auto mb-1 h-7 w-12 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative mx-auto h-3 w-20 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
          </div>
        ))}
      </div>

      {/* Badge section heading */}
      <div className="relative mb-4 h-5 w-20 overflow-hidden rounded bg-card border border-border">
        <div className="absolute inset-0 animate-shimmer" />
      </div>

      {/* Badge grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="relative overflow-hidden rounded-xl border border-border bg-card p-4">
            <div className="relative mx-auto mb-2 h-8 w-8 overflow-hidden rounded-full bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative mx-auto mt-2 h-4 w-20 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
