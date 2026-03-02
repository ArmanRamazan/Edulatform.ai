"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex min-h-[50vh] flex-col items-center justify-center px-4">
      <h1 className="mb-2 text-2xl font-bold text-red-600">Что-то пошло не так</h1>
      <p className="mb-6 text-gray-500">{error.message || "Произошла неизвестная ошибка"}</p>
      <button
        onClick={reset}
        className="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700"
      >
        Попробовать снова
      </button>
    </main>
  );
}
