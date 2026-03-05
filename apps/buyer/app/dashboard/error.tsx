"use client";

import { Header } from "@/components/Header";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-6">
        <div className="rounded-2xl border border-red-100 bg-red-50 p-8 text-center">
          <h2 className="mb-2 text-lg font-bold text-red-700">Что-то пошло не так</h2>
          <p className="mb-4 text-sm text-red-600">{error.message}</p>
          <button
            onClick={reset}
            className="rounded-xl bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:bg-red-700"
          >
            Попробовать снова
          </button>
        </div>
      </main>
    </>
  );
}
