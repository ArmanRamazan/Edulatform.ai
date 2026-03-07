"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  BookOpen,
  Flame,
  Brain,
  AlertCircle,
  BarChart2,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useMyVelocity } from "@/hooks/use-velocity";
import type { VelocityCourseProgress } from "@/lib/api";

const WeeklyConceptsChart = dynamic(() => import("./WeeklyConceptsChart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

const QuizScoreChart = dynamic(() => import("./QuizScoreChart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

// ── Skeleton helpers ──────────────────────────────────────────────────────────

function ChartSkeleton() {
  return (
    <div className="relative h-60 overflow-hidden rounded-lg border border-border bg-card">
      <div className="absolute inset-0 animate-shimmer" />
    </div>
  );
}

function MetricSkeleton() {
  return (
    <div className="relative h-28 overflow-hidden rounded-xl border border-border bg-card">
      <div className="absolute inset-0 animate-shimmer" />
    </div>
  );
}

// ── Trend icon ────────────────────────────────────────────────────────────────

function TrendIcon({ trend }: { trend: "up" | "down" | "stable" }) {
  if (trend === "up")
    return <TrendingUp className="h-4 w-4 text-success" aria-hidden="true" />;
  if (trend === "down")
    return <TrendingDown className="h-4 w-4 text-destructive" aria-hidden="true" />;
  return <Minus className="h-4 w-4 text-muted-foreground" aria-hidden="true" />;
}

// ── Retention colour (design-system semantic tokens) ──────────────────────────

function retentionColorClass(rate: number): string {
  if (rate >= 80) return "text-success";
  if (rate >= 60) return "text-warning";
  return "text-destructive";
}

// ── Course progress card ──────────────────────────────────────────────────────

function CourseProgressCard({ cp }: { cp: VelocityCourseProgress }) {
  const done = cp.mastery_pct >= 100;
  const pct = Math.min(cp.mastery_pct, 100);

  return (
    <div className="rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/30">
      <p className="mb-1 truncate text-sm font-medium text-foreground">
        Курс{" "}
        <span className="font-mono text-xs text-muted-foreground">
          {cp.course_id.slice(0, 8)}&hellip;
        </span>
      </p>
      <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-primary transition-all duration-700"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="tabular-nums">
          {cp.mastered}/{cp.total_concepts} концепций
        </span>
        {done ? (
          <span className="font-semibold text-success">Завершён</span>
        ) : (
          <span>~{cp.estimated_weeks_left} нед.</span>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function VelocityPage() {
  const { token, user, loading: authLoading } = useAuth();
  const { data, isLoading, error } = useMyVelocity(token);

  // ── Auth loading ──
  if (authLoading) {
    return (
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <MetricSkeleton />
          <MetricSkeleton />
          <MetricSkeleton />
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
      </div>
    );
  }

  // ── Unauthenticated ──
  if (!user) {
    return (
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-card py-16 text-center">
          <BarChart2
            className="h-10 w-10 text-muted-foreground/30"
            strokeWidth={1.5}
            aria-hidden="true"
          />
          <p className="text-sm text-muted-foreground">
            <Link
              href="/login"
              className="text-primary underline underline-offset-2 hover:text-primary/80"
            >
              Войдите
            </Link>
            , чтобы увидеть статистику обучения.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="mb-6 text-xl font-semibold text-foreground">Скорость обучения</h1>

      {/* ── Error banner — non-technical message only ── */}
      {error && (
        <div
          className="mb-6 flex items-center gap-3 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3"
          role="alert"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
          <div className="flex-1">
            <p className="text-sm font-medium text-destructive">
              Не удалось загрузить данные
            </p>
            <p className="text-xs text-muted-foreground">
              Проверьте подключение и обновите страницу
            </p>
          </div>
        </div>
      )}

      {/* ── Loading skeleton ── */}
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
          {/* ── Row 1 — Key metrics ── */}
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            {/* Concepts / week */}
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="mb-1 flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Концепций за неделю</span>
                <TrendIcon trend={data.trend} />
              </div>
              <p className="text-3xl font-semibold tabular-nums text-foreground">
                {data.concepts_mastered_this_week}
              </p>
              <p className="mt-1 text-xs text-muted-foreground/60">
                vs{" "}
                <span className="tabular-nums">{data.concepts_mastered_last_week}</span>{" "}
                на прошлой неделе
              </p>
            </div>

            {/* Streak */}
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="mb-1 flex items-center gap-2">
                <Flame className="h-3.5 w-3.5 text-warning" aria-hidden="true" />
                <span className="text-xs text-muted-foreground">Серия</span>
              </div>
              <p className="text-3xl font-semibold tabular-nums text-foreground">
                {data.streak_days}
                <span className="ml-1.5 text-base font-normal text-muted-foreground">дн.</span>
              </p>
            </div>

            {/* Retention */}
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="mb-1 flex items-center gap-2">
                <Brain className="h-3.5 w-3.5 text-info" aria-hidden="true" />
                <span className="text-xs text-muted-foreground">Запоминание</span>
              </div>
              <p
                className={`text-3xl font-semibold tabular-nums ${retentionColorClass(data.flashcard_retention_rate)}`}
              >
                {data.flashcard_retention_rate}
                <span className="ml-0.5 text-base font-normal text-muted-foreground">%</span>
              </p>
            </div>
          </div>

          {/* ── Row 2 — Charts ── */}
          {(data.quiz_score_trend.length > 0 || data.concepts_mastered_this_week > 0) && (
            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-card p-4">
                <h2 className="mb-3 text-sm font-semibold text-foreground">
                  Концепции по неделям
                </h2>
                <WeeklyConceptsChart
                  thisWeek={data.concepts_mastered_this_week}
                  lastWeek={data.concepts_mastered_last_week}
                />
              </div>
              <div className="rounded-xl border border-border bg-card p-4">
                <h2 className="mb-3 text-sm font-semibold text-foreground">
                  Результаты квизов
                </h2>
                <QuizScoreChart data={data.quiz_score_trend} />
              </div>
            </div>
          )}

          {/* ── Row 3 — Course progress ── */}
          {data.course_progress.length > 0 && (
            <section>
              <h2 className="mb-3 text-base font-semibold text-foreground">
                Прогресс по курсам
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {data.course_progress.map((cp) => (
                  <CourseProgressCard key={cp.course_id} cp={cp} />
                ))}
              </div>
            </section>
          )}

          {/* ── Empty — no data yet ── */}
          {data.course_progress.length === 0 &&
            data.quiz_score_trend.length === 0 &&
            data.concepts_mastered_this_week === 0 && (
              <div className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-card py-16 text-center">
                <BookOpen
                  className="h-10 w-10 text-muted-foreground/30"
                  strokeWidth={1.5}
                  aria-hidden="true"
                />
                <div className="max-w-[240px]">
                  <p className="text-sm font-medium text-muted-foreground">Нет данных</p>
                  <p className="mt-1 text-xs text-muted-foreground/60">
                    Начните учиться, чтобы увидеть свою статистику
                  </p>
                </div>
              </div>
            )}
        </>
      ) : null}
    </div>
  );
}
