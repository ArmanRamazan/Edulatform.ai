"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Header } from "@/components/Header";
import { useAuth } from "@/hooks/use-auth";
import { useMyVelocity } from "@/hooks/use-velocity";
import type { QuizScoreTrend, VelocityCourseProgress } from "@/lib/api";

const WeeklyConceptsChart = dynamic(() => import("./WeeklyConceptsChart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

const QuizScoreChart = dynamic(() => import("./QuizScoreChart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

function ChartSkeleton() {
  return (
    <div className="flex h-64 items-center justify-center rounded-lg bg-gray-50">
      <p className="text-sm text-gray-400">Загрузка графика...</p>
    </div>
  );
}

function MetricSkeleton() {
  return <div className="h-28 animate-pulse rounded-lg bg-gray-100" />;
}

function TrendArrow({ trend }: { trend: "up" | "down" | "stable" }) {
  if (trend === "up") return <span className="text-lg text-green-600">&uarr;</span>;
  if (trend === "down") return <span className="text-lg text-red-500">&darr;</span>;
  return <span className="text-lg text-gray-400">&mdash;</span>;
}

function retentionColor(rate: number): string {
  if (rate >= 80) return "text-green-600";
  if (rate >= 60) return "text-yellow-600";
  return "text-red-500";
}

function CourseProgressCard({ cp }: { cp: VelocityCourseProgress }) {
  const done = cp.mastery_pct >= 100;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="mb-1 text-sm font-medium text-gray-700">Курс {cp.course_id.slice(0, 8)}...</p>
      <div className="mb-2 h-2 overflow-hidden rounded-full bg-gray-200">
        <div
          className="h-full rounded-full bg-blue-500 transition-all"
          style={{ width: `${Math.min(cp.mastery_pct, 100)}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>
          {cp.mastered}/{cp.total_concepts} концепций
        </span>
        {done ? (
          <span className="font-semibold text-green-600">Завершён!</span>
        ) : (
          <span>Осталось ~{cp.estimated_weeks_left} недель</span>
        )}
      </div>
    </div>
  );
}

export default function VelocityPage() {
  const { token, user, loading: authLoading } = useAuth();
  const { data, isLoading, error } = useMyVelocity(token);

  if (authLoading) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-6xl px-4 py-6">
          <p className="text-gray-400">Загрузка...</p>
        </main>
      </>
    );
  }

  if (!user) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-6xl px-4 py-6">
          <p>
            <Link href="/login" className="text-blue-600 underline">
              Войдите
            </Link>
            , чтобы увидеть статистику.
          </p>
        </main>
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-6">
        <h1 className="mb-6 text-2xl font-bold">Скорость обучения</h1>

        {error && (
          <p className="mb-4 text-sm text-red-500">Ошибка загрузки: {(error as Error).message}</p>
        )}

        {isLoading ? (
          <>
            <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <MetricSkeleton />
              <MetricSkeleton />
              <MetricSkeleton />
            </div>
            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              <ChartSkeleton />
              <ChartSkeleton />
            </div>
          </>
        ) : data ? (
          <>
            {/* Row 1 — Key metrics */}
            <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-sm text-gray-500">Концепций за неделю</span>
                  <TrendArrow trend={data.trend} />
                </div>
                <p className="text-3xl font-bold">{data.concepts_mastered_this_week}</p>
                <p className="mt-1 text-xs text-gray-400">
                  vs {data.concepts_mastered_last_week} на прошлой неделе
                </p>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <p className="mb-1 text-sm text-gray-500">Серия</p>
                <p className="text-3xl font-bold">
                  <span className="mr-1">&#x1F525;</span>
                  {data.streak_days} дней подряд
                </p>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <p className="mb-1 text-sm text-gray-500">Запоминание</p>
                <p className={`text-3xl font-bold ${retentionColor(data.flashcard_retention_rate)}`}>
                  {data.flashcard_retention_rate}%
                </p>
              </div>
            </div>

            {/* Row 2 — Charts */}
            {(data.quiz_score_trend.length > 0 || data.concepts_mastered_this_week > 0) && (
              <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <h2 className="mb-3 text-sm font-semibold text-gray-700">Концепции по неделям</h2>
                  <WeeklyConceptsChart
                    thisWeek={data.concepts_mastered_this_week}
                    lastWeek={data.concepts_mastered_last_week}
                  />
                </div>
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <h2 className="mb-3 text-sm font-semibold text-gray-700">Результаты квизов</h2>
                  <QuizScoreChart data={data.quiz_score_trend} />
                </div>
              </div>
            )}

            {/* Row 3 — Course progress */}
            {data.course_progress.length > 0 && (
              <section>
                <h2 className="mb-3 text-lg font-semibold">Прогресс по курсам</h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {data.course_progress.map((cp) => (
                    <CourseProgressCard key={cp.course_id} cp={cp} />
                  ))}
                </div>
              </section>
            )}

            {data.course_progress.length === 0 &&
              data.quiz_score_trend.length === 0 &&
              data.concepts_mastered_this_week === 0 && (
                <p className="mt-8 text-center text-gray-400">
                  Начните учиться, чтобы увидеть свою статистику!
                </p>
              )}
          </>
        ) : null}
      </main>
    </>
  );
}
