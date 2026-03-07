"use client";

import { useAuth } from "@/hooks/use-auth";
import { useMyBadges, useMyXpHistory, useMyStreak } from "@/hooks/use-gamification";
import { Zap, Flame, Trophy } from "lucide-react";

const BADGE_ICONS: Record<string, string> = {
  first_enrollment: "\uD83C\uDF93",
  streak_7: "\uD83D\uDD25",
  quiz_ace: "\u2B50",
  mastery_100: "\uD83C\uDFC6",
};

const BADGE_LABELS: Record<string, string> = {
  first_enrollment: "Первый курс",
  streak_7: "7 дней подряд",
  quiz_ace: "Идеальный тест",
  mastery_100: "Полное мастерство",
};

const ALL_BADGES = ["first_enrollment", "streak_7", "quiz_ace", "mastery_100"];

function StatCard({
  icon: Icon,
  value,
  label,
  colorClass,
}: {
  icon: React.ComponentType<{ className?: string }>;
  value: number;
  label: string;
  colorClass: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 text-center">
      <Icon className={`mx-auto mb-2 h-5 w-5 ${colorClass}`} aria-hidden="true" />
      <p className={`text-2xl font-bold tabular-nums ${colorClass}`}>{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function BadgesSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Loading badges">
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="relative overflow-hidden rounded-xl border border-border bg-card p-4 text-center">
            <div className="relative mx-auto mb-2 h-5 w-5 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative mx-auto mb-1 h-7 w-12 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative mx-auto h-3 w-20 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="relative overflow-hidden rounded-xl border border-border bg-card p-4 text-center">
            <div className="relative mx-auto mb-2 h-8 w-8 overflow-hidden rounded-full bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative mx-auto mt-2 h-4 w-20 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function BadgesPage() {
  const { token, loading } = useAuth();
  const { data: badgeData, isLoading: badgesLoading } = useMyBadges(token);
  const { data: xpData, isLoading: xpLoading } = useMyXpHistory(token, { limit: 10 });
  const { data: streakData } = useMyStreak(token);

  const unlockedTypes = new Set(badgeData?.badges.map((b) => b.badge_type) ?? []);

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-6 text-2xl font-bold text-foreground">Достижения</h1>

      {(loading || badgesLoading) && <BadgesSkeleton />}

      {!loading && !badgesLoading && (
        <div className="space-y-8">
          {/* Stats summary */}
          <div className="grid grid-cols-3 gap-4">
            <StatCard
              icon={Zap}
              value={xpData?.total_xp ?? 0}
              label="Всего XP"
              colorClass="text-primary"
            />
            <StatCard
              icon={Flame}
              value={streakData?.current_streak ?? 0}
              label="Текущая серия (дн.)"
              colorClass="text-warning"
            />
            <StatCard
              icon={Trophy}
              value={streakData?.longest_streak ?? 0}
              label="Лучшая серия (дн.)"
              colorClass="text-success"
            />
          </div>

          {/* Badge shelf */}
          <section>
            <h2 className="mb-4 text-lg font-semibold text-foreground">Значки</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {ALL_BADGES.map((type) => {
                const unlocked = unlockedTypes.has(type);
                const badge = badgeData?.badges.find((b) => b.badge_type === type);
                return (
                  <div
                    key={type}
                    className={[
                      "flex flex-col items-center rounded-xl border p-4 transition-all",
                      unlocked
                        ? "border-warning/30 bg-warning/5"
                        : "border-border bg-card opacity-40",
                    ].join(" ")}
                  >
                    <span className="text-3xl" aria-hidden="true">
                      {BADGE_ICONS[type] ?? "\uD83C\uDFC5"}
                    </span>
                    <p className="mt-2 text-center text-sm font-medium text-foreground">
                      {BADGE_LABELS[type] ?? type}
                    </p>
                    {unlocked && badge ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        {new Date(badge.unlocked_at).toLocaleDateString("ru")}
                      </p>
                    ) : (
                      <p className="mt-1 text-xs text-muted-foreground/50">Не получен</p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* Recent XP events */}
          <section>
            <h2 className="mb-4 text-lg font-semibold text-foreground">Последние XP</h2>
            {xpLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="relative h-10 overflow-hidden rounded-lg border border-border bg-card">
                    <div className="absolute inset-0 animate-shimmer" />
                  </div>
                ))}
              </div>
            ) : !xpData || xpData.events.length === 0 ? (
              <div className="rounded-xl border border-border bg-card py-8 text-center">
                <Zap
                  className="mx-auto mb-2 h-8 w-8 text-muted-foreground/30"
                  aria-hidden="true"
                  strokeWidth={1.5}
                />
                <p className="text-sm text-muted-foreground">Пока нет очков опыта</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {xpData.events.map((ev, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-2.5 transition-colors hover:bg-muted/30"
                  >
                    <div>
                      <span className="text-sm font-medium text-foreground">
                        {xpActionLabel(ev.action)}
                      </span>
                      <span className="ml-2 text-xs text-muted-foreground">
                        {new Date(ev.created_at).toLocaleString("ru")}
                      </span>
                    </div>
                    <span className="font-semibold text-primary">+{ev.points} XP</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function xpActionLabel(action: string): string {
  switch (action) {
    case "lesson_complete":
      return "Урок пройден";
    case "quiz_submit":
      return "Тест выполнен";
    case "flashcard_review":
      return "Повторение карточки";
    default:
      return action;
  }
}
