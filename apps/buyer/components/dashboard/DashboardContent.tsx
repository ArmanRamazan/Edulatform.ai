"use client";

import Link from "next/link";
import { AlertCircle, BookOpen, CheckCircle2, RefreshCw } from "lucide-react";
import { motion, type Variants } from "framer-motion";
import { useAuth } from "@/hooks/use-auth";
import { useDailySummary, useStartMission, useMissionHistory } from "@/hooks/use-daily";
import { StreakBadge } from "./StreakBadge";
import { TrustLevelCard } from "./TrustLevelCard";
import { MissionCard } from "./MissionCard";

// ---------------------------------------------------------------------------
// Skeleton — matches layout shape exactly, uses design token colors
// ---------------------------------------------------------------------------
function CardSkeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-card border border-border ${className}`}
      aria-hidden="true"
    >
      <div className="absolute inset-0 animate-shimmer" />
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading dashboard">
      {/* Greeting row */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="relative h-7 w-56 overflow-hidden rounded-lg bg-card border border-border">
            <div className="absolute inset-0 animate-shimmer" />
          </div>
          <div className="relative h-4 w-36 overflow-hidden rounded bg-card border border-border">
            <div className="absolute inset-0 animate-shimmer" />
          </div>
        </div>
        <div className="relative h-8 w-24 overflow-hidden rounded-full bg-card border border-border">
          <div className="absolute inset-0 animate-shimmer" />
        </div>
      </div>
      {/* Main grid */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <CardSkeleton className="h-56" />
        <CardSkeleton className="h-56" />
      </div>
      {/* Bottom row */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <CardSkeleton className="h-44" />
        <CardSkeleton className="h-44" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stagger animation helpers
// ---------------------------------------------------------------------------
const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

// ---------------------------------------------------------------------------
// DashboardContent
// ---------------------------------------------------------------------------
export function DashboardContent() {
  const { token, user, loading: authLoading } = useAuth();
  const { data: summary, isLoading, error, refetch } = useDailySummary(token);
  const startMission = useStartMission(token);
  const { data: history } = useMissionHistory(token, 5);

  // ── Loading states ──────────────────────────────────────────────────────
  if (authLoading || isLoading) {
    return <DashboardSkeleton />;
  }

  // ── Unauthenticated ─────────────────────────────────────────────────────
  if (!user) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center text-center">
        <BookOpen
          className="mb-4 h-12 w-12 text-muted-foreground"
          aria-hidden="true"
          strokeWidth={1.5}
        />
        <h2 className="mb-2 text-xl font-bold text-foreground">
          Добро пожаловать в KnowledgeOS
        </h2>
        <p className="mb-6 text-sm text-muted-foreground">
          Войдите, чтобы увидеть свой прогресс обучения
        </p>
        <Link
          href="/login"
          className="rounded-xl bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Войти
        </Link>
      </div>
    );
  }

  // ── Error state ─────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center p-6">
        <div className="flex max-w-sm flex-col items-center gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertCircle className="h-6 w-6 text-destructive" aria-hidden="true" />
          </div>
          <h3 className="text-sm font-semibold text-foreground">Не удалось загрузить данные</h3>
          <p className="text-xs text-muted-foreground">
            Проверьте подключение к интернету и попробуйте снова.
          </p>
          <button
            onClick={() => void refetch()}
            className="mt-1 inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  // ── Empty / no data ──────────────────────────────────────────────────────
  if (!summary) return null;

  function handleStartMission() {
    if (!summary?.mission) return;
    startMission.mutate(summary.mission.id);
  }

  const completedMissions = history?.items.filter((m) => m.status === "completed") ?? [];

  return (
    <motion.div
      className="space-y-6"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {/* Greeting row */}
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{summary.greeting}</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">Ваш прогресс за сегодня</p>
        </div>
        <StreakBadge days={summary.streak_days} />
      </motion.div>

      {/* Main grid */}
      <motion.div variants={item} className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <TrustLevelCard trustLevel={summary.trust_level} />
        <MissionCard
          mission={summary.mission}
          onStart={handleStartMission}
          isStarting={startMission.isPending}
        />
      </motion.div>

      {/* Bottom row */}
      <motion.div variants={item} className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {/* Flashcards due */}
        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-border/80">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Карточки
            </span>
            <BookOpen
              className="h-5 w-5 text-muted-foreground/50"
              aria-hidden="true"
              strokeWidth={1.5}
            />
          </div>
          <p className="text-3xl font-bold tabular-nums text-foreground">
            {summary.due_flashcards}
          </p>
          <p className="mb-4 text-sm text-muted-foreground">
            {summary.due_flashcards === 0
              ? "Все карточки повторены!"
              : `${cardWord(summary.due_flashcards)} к повторению`}
          </p>
          {summary.due_flashcards > 0 && (
            <Link
              href="/flashcards"
              className="inline-flex items-center gap-1 rounded-xl bg-primary/10 px-4 py-2 text-sm font-semibold text-primary ring-1 ring-primary/20 transition-all hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Повторить
              <span aria-hidden="true">→</span>
            </Link>
          )}
          {summary.due_flashcards === 0 && (
            <div className="inline-flex items-center gap-1.5 text-xs text-success">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              Отличная работа!
            </div>
          )}
        </div>

        {/* Mission History */}
        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-border/80">
          <span className="mb-3 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            История миссий
          </span>
          {completedMissions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-6 text-center">
              <CheckCircle2
                className="mb-2 h-8 w-8 text-muted-foreground/30"
                aria-hidden="true"
                strokeWidth={1.5}
              />
              <p className="text-sm text-muted-foreground">Пока нет завершённых миссий</p>
            </div>
          ) : (
            <ul className="space-y-1">
              {completedMissions.map((m) => (
                <li
                  key={m.id}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-muted/50"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-success/15 text-xs text-success">
                    ✓
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {m.blueprint?.concept_name ?? "Миссия"}
                    </p>
                    {m.completed_at && (
                      <p className="text-xs text-muted-foreground">
                        {new Date(m.completed_at).toLocaleDateString("ru")}
                      </p>
                    )}
                  </div>
                  {m.score !== null && (
                    <span className="shrink-0 text-sm font-semibold tabular-nums text-success">
                      {m.score}%
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

function cardWord(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return `${n} карточек`;
  if (mod10 === 1) return `${n} карточка`;
  if (mod10 >= 2 && mod10 <= 4) return `${n} карточки`;
  return `${n} карточек`;
}
