"use client";

import { use } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { useBundle } from "@/hooks/_deprecated/use-bundles";
import type { Course } from "@/lib/api";

const LEVEL_LABELS: Record<string, string> = {
  beginner: "Начальный",
  intermediate: "Средний",
  advanced: "Продвинутый",
};

const LEVEL_COLORS: Record<string, string> = {
  beginner: "bg-green-100 text-green-700",
  intermediate: "bg-yellow-100 text-yellow-700",
  advanced: "bg-red-100 text-red-700",
};

function BundleCourseCard({ course }: { course: Course }) {
  return (
    <Link
      href={`/courses/${course.id}`}
      className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-4 transition hover:shadow-md"
    >
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-gray-900 line-clamp-1">
          {course.title}
        </h3>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500">
          <span
            className={`rounded px-1.5 py-0.5 text-xs font-medium ${LEVEL_COLORS[course.level] ?? ""}`}
          >
            {LEVEL_LABELS[course.level] ?? course.level}
          </span>
          <span>{course.duration_minutes} мин</span>
          {course.avg_rating != null && (
            <span>
              ★ {course.avg_rating.toFixed(1)} ({course.review_count})
            </span>
          )}
        </div>
      </div>
      <div className="shrink-0 text-right">
        {course.is_free ? (
          <span className="text-sm font-medium text-green-600">Бесплатно</span>
        ) : (
          <span className="text-sm font-semibold text-gray-700">
            {course.price} ₽
          </span>
        )}
      </div>
    </Link>
  );
}

export default function BundleDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: bundle, isLoading, error } = useBundle(id);

  const totalPrice =
    bundle?.courses.reduce(
      (sum, c) => sum + (c.is_free ? 0 : (c.price ?? 0)),
      0,
    ) ?? 0;
  const savings = totalPrice - (bundle?.price ?? 0);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-8">
        {isLoading && (
          <div className="space-y-4">
            <div className="h-8 w-2/3 animate-pulse rounded bg-gray-200" />
            <div className="h-4 w-full animate-pulse rounded bg-gray-200" />
            <div className="h-32 animate-pulse rounded bg-gray-200" />
          </div>
        )}

        {error && (
          <p className="text-red-600">
            Ошибка загрузки: {(error as Error).message}
          </p>
        )}

        {bundle && (
          <>
            <Link
              href="/bundles"
              className="mb-4 inline-block text-sm text-blue-600 hover:underline"
            >
              ← Все наборы
            </Link>

            <h1 className="mb-2 text-2xl font-bold">{bundle.title}</h1>
            <p className="mb-6 text-gray-600">{bundle.description}</p>

            <div className="mb-6 rounded-lg border border-gray-200 bg-white p-5">
              <div className="flex flex-wrap items-center gap-4">
                <div>
                  <span className="text-sm text-gray-500 line-through">
                    Отдельно: {totalPrice} ₽
                  </span>
                </div>
                <div>
                  <span className="text-2xl font-bold text-blue-600">
                    В наборе: {bundle.price} ₽
                  </span>
                </div>
                {savings > 0 && (
                  <span className="rounded bg-green-100 px-3 py-1 text-sm font-semibold text-green-700">
                    Экономия: {savings} ₽ ({bundle.discount_percent}%)
                  </span>
                )}
              </div>

              <button className="mt-4 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700">
                Купить набор
              </button>
            </div>

            <h2 className="mb-3 text-lg font-semibold">
              Курсы в наборе ({bundle.courses.length})
            </h2>
            <div className="space-y-3">
              {bundle.courses.map((course) => (
                <BundleCourseCard key={course.id} course={course} />
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}
