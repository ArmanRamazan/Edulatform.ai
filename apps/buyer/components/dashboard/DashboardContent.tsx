"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useDailySummary, useStartMission, useMissionHistory } from "@/hooks/use-daily";
import { StreakBadge } from "./StreakBadge";
import { TrustLevelCard } from "./TrustLevelCard";
import { MissionCard } from "./MissionCard";

function CardSkeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded-2xl bg-gray-100 ${className}`} />
  );
}

export function DashboardContent() {
  const { token, user, loading: authLoading } = useAuth();
  const { data: summary, isLoading, error } = useDailySummary(token);
  const startMission = useStartMission(token);
  const { data: history } = useMissionHistory(token, 5);

  if (authLoading) {
    return <DashboardSkeleton />;
  }

  if (!user) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center text-center">
        <span className="mb-4 text-5xl">&#x1F393;</span>
        <h2 className="mb-2 text-xl font-bold text-gray-800">Добро пожаловать в EduPlatform</h2>
        <p className="mb-6 text-sm text-gray-500">Войдите, чтобы увидеть свой прогресс обучения</p>
        <Link
          href="/login"
          className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Войти
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-100 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-600">
          Ошибка загрузки: {(error as Error).message}
        </p>
      </div>
    );
  }

  if (!summary) return null;

  function handleStartMission() {
    if (!summary?.mission) return;
    startMission.mutate(summary.mission.id);
  }

  const completedMissions = history?.items.filter((m) => m.status === "completed") ?? [];

  return (
    <div className="space-y-6">
      {/* Greeting row */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{summary.greeting}</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Ваш прогресс за сегодня
          </p>
        </div>
        <StreakBadge days={summary.streak_days} />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {/* Trust Level */}
        <TrustLevelCard trustLevel={summary.trust_level} />

        {/* Today's Mission */}
        <MissionCard
          mission={summary.mission}
          onStart={handleStartMission}
          isStarting={startMission.isPending}
        />
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {/* Flashcards due */}
        <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-gray-100">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Карточки
            </span>
            <span className="text-2xl" role="img" aria-label="cards">&#x1F4DA;</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">{summary.due_flashcards}</p>
          <p className="mb-4 text-sm text-gray-500">
            {summary.due_flashcards === 0
              ? "Все карточки повторены!"
              : `${cardWord(summary.due_flashcards)} к повторению`}
          </p>
          {summary.due_flashcards > 0 && (
            <Link
              href="/flashcards"
              className="inline-flex items-center gap-1 rounded-xl bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-700 ring-1 ring-violet-200 transition-colors hover:bg-violet-100"
            >
              Повторить
              <span aria-hidden="true">&rarr;</span>
            </Link>
          )}
        </div>

        {/* Mission History */}
        <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-gray-100">
          <span className="mb-3 block text-xs font-medium uppercase tracking-wider text-gray-400">
            История миссий
          </span>
          {completedMissions.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-400">
              Пока нет завершённых миссий
            </p>
          ) : (
            <ul className="space-y-2">
              {completedMissions.map((m) => (
                <li
                  key={m.id}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-gray-50"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs text-emerald-600">
                    &#x2713;
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-700">
                      {m.blueprint?.concept_name ?? "Миссия"}
                    </p>
                    {m.completed_at && (
                      <p className="text-xs text-gray-400">
                        {new Date(m.completed_at).toLocaleDateString("ru")}
                      </p>
                    )}
                  </div>
                  {m.score !== null && (
                    <span className="shrink-0 text-sm font-semibold text-emerald-600">
                      {m.score}%
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="h-7 w-56 animate-pulse rounded-lg bg-gray-200" />
          <div className="mt-2 h-4 w-36 animate-pulse rounded bg-gray-100" />
        </div>
        <div className="h-8 w-24 animate-pulse rounded-full bg-gray-200" />
      </div>
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <CardSkeleton className="h-56" />
        <CardSkeleton className="h-56" />
      </div>
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <CardSkeleton className="h-44" />
        <CardSkeleton className="h-44" />
      </div>
    </div>
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
