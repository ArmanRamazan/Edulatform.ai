export default function CourseDetailLoading() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-4 h-4 w-32 animate-pulse rounded bg-gray-200" />
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="mb-4 h-8 w-2/3 animate-pulse rounded bg-gray-200" />
        <div className="mb-3 flex gap-3">
          <div className="h-5 w-20 animate-pulse rounded bg-gray-200" />
          <div className="h-5 w-16 animate-pulse rounded bg-gray-200" />
          <div className="h-5 w-24 animate-pulse rounded bg-gray-200" />
        </div>
        <div className="space-y-2">
          <div className="h-4 w-full animate-pulse rounded bg-gray-100" />
          <div className="h-4 w-5/6 animate-pulse rounded bg-gray-100" />
          <div className="h-4 w-4/6 animate-pulse rounded bg-gray-100" />
        </div>
        <div className="mt-6 h-10 w-40 animate-pulse rounded bg-gray-200" />
      </div>
    </main>
  );
}
