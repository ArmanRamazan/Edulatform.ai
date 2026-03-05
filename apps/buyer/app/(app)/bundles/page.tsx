"use client";

import Link from "next/link";
import { Header } from "@/components/Header";
import { useBundleList } from "@/hooks/use-bundles";
import type { CourseBundle } from "@/lib/api";

function BundleCard({ bundle }: { bundle: CourseBundle }) {
  return (
    <Link
      href={`/bundles/${bundle.id}`}
      className="block rounded-lg border border-gray-200 bg-white p-5 transition hover:shadow-md"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="text-lg font-semibold text-gray-900 line-clamp-1">
          {bundle.title}
        </h3>
        {bundle.discount_percent > 0 && (
          <span className="shrink-0 rounded bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">
            -{bundle.discount_percent}%
          </span>
        )}
      </div>

      <p className="mb-4 text-sm text-gray-600 line-clamp-2">
        {bundle.description}
      </p>

      <div className="flex items-center justify-between">
        <span className="text-lg font-bold text-blue-600">
          {bundle.price} ₽
        </span>
        <span className="text-sm text-blue-600 hover:underline">
          Подробнее →
        </span>
      </div>
    </Link>
  );
}

export default function BundlesPage() {
  const { data, isLoading, error } = useBundleList({ limit: 20 });

  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-bold">Наборы курсов</h1>

        {isLoading && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-40 animate-pulse rounded-lg bg-gray-200"
              />
            ))}
          </div>
        )}

        {error && (
          <p className="text-red-600">
            Ошибка загрузки: {(error as Error).message}
          </p>
        )}

        {data && data.items.length === 0 && (
          <p className="text-gray-500">Пока нет доступных наборов</p>
        )}

        {data && data.items.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((bundle) => (
              <BundleCard key={bundle.id} bundle={bundle} />
            ))}
          </div>
        )}
      </main>
    </>
  );
}
