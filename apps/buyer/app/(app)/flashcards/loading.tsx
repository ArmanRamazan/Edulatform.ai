export default function FlashcardsLoading() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-8" aria-busy="true" aria-label="Loading flashcards">
      {/* Title */}
      <div className="relative mb-6 h-8 w-56 overflow-hidden rounded-lg bg-card border border-border">
        <div className="absolute inset-0 animate-shimmer" />
      </div>
      {/* Counter */}
      <div className="relative mb-4 h-4 w-32 overflow-hidden rounded bg-card border border-border">
        <div className="absolute inset-0 animate-shimmer" />
      </div>
      {/* Progress bar */}
      <div className="relative mb-4 h-1 overflow-hidden rounded-full bg-secondary">
        <div className="absolute inset-0 animate-shimmer" />
      </div>
      {/* Card */}
      <div className="relative min-h-[220px] overflow-hidden rounded-2xl border-2 border-border bg-card p-8">
        <div className="flex flex-col items-center justify-center gap-3">
          <div className="relative h-3 w-16 overflow-hidden rounded bg-secondary">
            <div className="absolute inset-0 animate-shimmer" />
          </div>
          <div className="relative h-6 w-56 overflow-hidden rounded bg-secondary">
            <div className="absolute inset-0 animate-shimmer" />
          </div>
          <div className="relative mt-4 h-3 w-44 overflow-hidden rounded bg-secondary">
            <div className="absolute inset-0 animate-shimmer" />
          </div>
        </div>
      </div>
    </div>
  );
}
