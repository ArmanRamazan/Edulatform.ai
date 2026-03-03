export default function FlashcardsLoading() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 h-7 w-56 animate-pulse rounded bg-gray-200" />
      <div className="mb-4 h-4 w-32 animate-pulse rounded bg-gray-200" />
      <div className="min-h-[200px] rounded-xl border-2 border-gray-200 p-8">
        <div className="flex flex-col items-center justify-center gap-3">
          <div className="h-3 w-16 animate-pulse rounded bg-gray-200" />
          <div className="h-5 w-48 animate-pulse rounded bg-gray-200" />
          <div className="mt-4 h-3 w-40 animate-pulse rounded bg-gray-100" />
        </div>
      </div>
    </div>
  );
}
