"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useMyEnrollments } from "@/hooks/use-enrollments";

const STATUS_LABELS: Record<string, string> = {
  enrolled: "Записан",
  in_progress: "В процессе",
  completed: "Завершён",
};

export default function EnrollmentsPage() {
  const { token, user, loading } = useAuth();
  const { data, isLoading } = useMyEnrollments(token, { limit: 50 });

  return (
    <main className="mx-auto max-w-4xl px-4 py-6">
        <h1 className="mb-4 text-2xl font-bold">Мои курсы</h1>

        {loading || isLoading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : !user ? (
          <p className="text-gray-500">
            <Link href="/login" className="text-blue-600 hover:underline">
              Войдите
            </Link>{" "}
            чтобы увидеть свои курсы.
          </p>
        ) : !data || data.items.length === 0 ? (
          <p className="text-gray-500">
            Вы ещё не записаны ни на один курс.{" "}
            <Link href="/" className="text-blue-600 hover:underline">
              Посмотреть курсы
            </Link>
          </p>
        ) : (
          <>
            <p className="mb-4 text-sm text-gray-400">Всего: {data.total}</p>
            <div className="space-y-3">
              {data.items.map((e) => (
                <Link
                  key={e.id}
                  href={`/courses/${e.course_id}`}
                  className="block rounded-lg border border-gray-200 bg-white p-4 hover:border-blue-300"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      Курс: {e.course_id.slice(0, 8)}...
                    </span>
                    <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                      {STATUS_LABELS[e.status] || e.status}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-400">
                    Записан: {new Date(e.enrolled_at).toLocaleDateString("ru")}
                  </p>
                </Link>
              ))}
            </div>
          </>
        )}
      </main>
  );
}
