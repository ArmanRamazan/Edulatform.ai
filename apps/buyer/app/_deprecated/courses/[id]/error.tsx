"use client";

import Link from "next/link";

export default function CourseError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 text-center">
      <h1 className="mb-2 text-xl font-bold text-red-600">Не удалось загрузить курс</h1>
      <p className="mb-6 text-gray-500">{error.message || "Произошла ошибка"}</p>
      <div className="flex items-center justify-center gap-3">
        <button
          onClick={reset}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
        >
          Попробовать снова
        </button>
        <Link href="/" className="text-sm text-blue-600 hover:underline">
          Вернуться к курсам
        </Link>
      </div>
    </main>
  );
}
